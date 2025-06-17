#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.foreman.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     02 Jan 2019, (7:21 AM)

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import hashlib
import json
import threading
import queue
from datetime import datetime

import schedule

from unmanic.libs import common
from unmanic.libs.library import Library
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.worker_group import WorkerGroup
from unmanic.libs.workers import Worker


class Foreman(threading.Thread):
    def __init__(self, data_queues, settings, task_queue, event):
        super(Foreman, self).__init__(name='Foreman')
        self.settings = settings
        self.event = event
        self.task_queue = task_queue
        self.data_queues = data_queues
        self.logger = data_queues["logging"].get_logger(self.name)
        self.complete_queue = data_queues["processedtasks"]
        self.pendingtasks = data_queues["pendingtasks"]
        self.worker_threads = {}
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        self.scheduler = schedule.Scheduler()
        self.idle_workers = threading.Semaphore(0)

        self.scheduler.every(30).seconds.do(self.manage_event_schedules)
        self.scheduler.every(60).seconds.do(self.prune_dead_threads)

        # Set the current plugin config
        self.current_config = {
            'settings':      {},
            'settings_hash': ''
        }
        self.configuration_changed()

    def _log(self, message, message2=None, level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()
        self.idle_workers.release()
        self.pendingtasks.shutdown(immediate=True)

        # Stop all workers
        # To avoid having the dictionary change size during iteration,
        #   we need to first get the thread_keys, then iterate through that
        thread_keys = list(self.worker_threads.keys())
        for thread in thread_keys:
            self.mark_worker_thread_as_redundant(thread)

    def get_total_worker_count(self):
        """Returns the worker count as an integer"""
        worker_count = 0
        for worker_group in WorkerGroup.get_all_worker_groups():
            worker_count += worker_group.get('number_of_workers', 0)
        print(f"Total number of workers: {worker_count}")
        return int(worker_count)

    def save_current_config(self, settings=None, settings_hash=None):
        if settings:
            self.current_config['settings'] = settings
        if settings_hash:
            self.current_config['settings_hash'] = settings_hash
        self._log('Updated config. If this is modified, all workers will be paused', level='debug')

    def get_current_library_configuration(self):
        # Fetch all libraries
        all_plugin_settings = {}
        for library in Library.get_all_libraries():
            try:
                library_config = Library(library.get('id'))
            except Exception as e:
                self._log("Unable to fetch library config for ID {}".format(library.get('id')), level='exception')
                continue
            # Get list of enabled plugins with their settings
            enabled_plugins = []
            for enabled_plugin in library_config.get_enabled_plugins(include_settings=True):
                enabled_plugins.append({
                    'plugin_id': enabled_plugin.get('plugin_id'),
                    'settings':  enabled_plugin.get('settings'),
                })

            # Get the plugin flow
            plugin_flow = library_config.get_plugin_flow()

            # Append this library's plugin config and flow the the dictionary
            all_plugin_settings[library.get('id')] = {
                'enabled_plugins': enabled_plugins,
                'plugin_flow':     plugin_flow,
            }
        return all_plugin_settings

    def configuration_changed(self):
        current_settings = self.get_current_library_configuration()
        # Compare current settings with foreman recorded settings.
        json_encoded_settings = json.dumps(current_settings, sort_keys=True).encode()
        current_settings_hash = hashlib.md5(json_encoded_settings).hexdigest()
        if current_settings_hash == self.current_config.get('settings_hash', ''):
            return False
        # Record current settings
        self.save_current_config(settings=current_settings, settings_hash=current_settings_hash)
        # Settings have changed
        return True

    def validate_worker_config(self):
        valid = True
        frontend_messages = self.data_queues.get('frontend_messages')

        # Ensure that the enabled plugins are compatible with the PluginHandler version
        plugin_handler = PluginsHandler()
        if plugin_handler.get_incompatible_enabled_plugins(frontend_messages):
            valid = False

        # Check if plugin configuration has been modified. If it has, stop the workers.
        # What we want to avoid here is someone partially modifying the plugin configuration
        #   and having the workers pickup a job mid configuration.
        if self.configuration_changed():
            # Generate a frontend message and falsify validation
            frontend_messages.put(
                {
                    'id':      'pluginSettingsChangeWorkersStopped',
                    'type':    'warning',
                    'code':    'pluginSettingsChangeWorkersStopped',
                    'message': '',
                    'timeout': 0
                }
            )
            valid = False

        # Ensure library config is within limits
        if not Library.within_library_count_limits(frontend_messages):
            valid = False

        return valid

    def on_worker_config_changed(self):
        self.init_worker_threads()

    def run_task(self, time_now, task, worker_count, worker_group):
        worker_group_id = worker_group.get_id()
        self.last_schedule_run = time_now
        if task == 'pause':
            # Pause all workers now
            self._log("Running scheduled event - Pause all worker threads", level='debug')
            self.pause_all_worker_threads(worker_group_id=worker_group_id)
        elif task == 'resume':
            # Resume all workers now
            self._log("Running scheduled event - Resume all worker threads", level='debug')
            self.resume_all_worker_threads(worker_group_id=worker_group_id)
        elif task == 'count':
            # Set the worker count value
            # Save the settings so this scheduled event will persist an application restart
            self._log("Running scheduled event - Setting worker count to '{}'".format(worker_count), level='debug')
            worker_group.set_number_of_workers(worker_count)
            worker_group.save()

    def manage_event_schedules(self):
        """
        Manage all scheduled worker events
        This function limits itself to run only once every 60 seconds

        :return:
        """
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_of_week = datetime.today().today().weekday()
        time_now = datetime.today().strftime('%H:%M')
        did_something = False
        for wg in WorkerGroup.get_all_worker_groups():
            try:
                worker_group = WorkerGroup(group_id=wg.get('id'))
                event_schedules = worker_group.get_worker_event_schedules()
            except Exception as e:
                self._log("While iterating through the worker groups, the worker group disappeared", str(e), level='debug')
                continue

            for event_schedule in event_schedules:
                schedule_time = event_schedule.get('schedule_time')
                # Ensure we have a schedule time
                if not schedule_time:
                    continue
                # Ensure the schedule time is now
                if time_now != schedule_time:
                    continue

                repetition = event_schedule.get('repetition')
                # Ensure we have a repetition
                if not repetition:
                    continue

                # Check if it should run
                if repetition == 'daily':
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)
                elif repetition == 'weekday' and days[day_of_week] not in ['saturday', 'sunday']:
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)
                elif repetition == 'weekend' and days[day_of_week] in ['saturday', 'sunday']:
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)
                elif repetition == days[day_of_week]:
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)
                else:
                    continue
                did_something = True
        if did_something:
            self.init_worker_threads()

    def prune_dead_threads(self):
        # Remove any redundant idle workers from our list
        # To avoid having the dictionary change size during iteration,
        # we need to first get the thread_keys, then iterate through that
        for thread in list(self.worker_threads.keys()):
            if thread in self.worker_threads:
                if not self.worker_threads[thread].is_alive():
                    print(f"pruning {thread}")
                    del self.worker_threads[thread]

    def init_worker_threads(self):
        self.prune_dead_threads()

        # Check that we have enough workers running. Spawn new ones as required.
        worker_group_ids = set()
        worker_group_names = set()
        for worker_group in WorkerGroup.get_all_worker_groups():
            worker_group_ids.add(worker_group.get('id'))

            # Create threads as required
            for i in range(worker_group.get('number_of_workers')):
                worker_id = "{}-{}".format(worker_group.get('name'), i)
                worker_name = "{}-Worker-{}".format(worker_group.get('name'), (i + 1))
                # Add this name to a list. If the name changes, we can remove old incorrectly named workers
                worker_group_names.add(worker_name)
                if worker_id not in self.worker_threads:
                    # This worker does not yet exist, create it
                    self.start_worker_thread(worker_id, worker_name, worker_group.get('id'))
                    print(f"started {worker_id}")

            # Remove any workers that do not belong. The max number of supported workers is 12
            for i in range(worker_group.get('number_of_workers'), 12):
                worker_id = "{}-{}".format(worker_group.get('name'), i)
                if worker_id in self.worker_threads:
                    # Only remove threads that are idle (never terminate a task just to reduce worker count)
                    is_idle = self.worker_threads[worker_id].idle
                    self.mark_worker_thread_as_redundant(worker_id, immediate=is_idle)

        # Remove workers for groups that no longer exist
        for thread in self.worker_threads:
            worker_group_id = self.worker_threads[thread].worker_group_id
            worker_name = self.worker_threads[thread].name
            if worker_group_id not in worker_group_ids or worker_name not in worker_group_names:
                # Only remove threads that are idle (never terminate a task just to reduce worker count)
                is_idle = self.worker_threads[thread].idle
                self.mark_worker_thread_as_redundant(thread, immediate=is_idle)
                print(f"stopping {thread}")

    def start_worker_thread(self, worker_id, worker_name, worker_group):
        thread = Worker(worker_id, worker_name, worker_group, self.complete_queue, self.event, self.idle_workers)
        thread.daemon = True
        thread.start()
        self.worker_threads[worker_id] = thread

    def fetch_available_worker_ids(self):
        tread_ids = []
        for thread in self.worker_threads:
            if self.worker_threads[thread].idle and self.worker_threads[thread].is_alive():
                if not self.worker_threads[thread].paused:
                    tread_ids.append(self.worker_threads[thread].thread_id)
        return tread_ids

    def check_for_idle_workers(self):
        for thread in self.worker_threads:
            if self.worker_threads[thread].idle and self.worker_threads[thread].is_alive():
                if not self.worker_threads[thread].paused:
                    return True
        return False

    def get_tags_configured_for_worker(self, worker_id):
        """Fetch the tags for a given worker ID"""
        assigned_worker_group_id = self.worker_threads[worker_id].worker_group_id
        worker_group = WorkerGroup(group_id=assigned_worker_group_id)
        return worker_group.get_tags()

    def postprocessor_queue_full(self):
        """
        Check if Post-processor queue is greater than the number of workers enabled.
        If it is, return True. Else False.

        :return:
        """
        frontend_messages = self.data_queues.get('frontend_messages')
        # Use the configured worker count + 1 as the post-processor queue limit
        limit = (int(self.get_total_worker_count()) + 1)
        # Include a count of all available and busy remote workers for the postprocessor queue limit
        current_count = len(self.task_queue.list_processed_tasks())
        if current_count > limit:
            msg = "There are currently {} items in the post-processor queue. Halting feeding workers until it drops below {}."
            self._log(msg.format(current_count, limit), level='warning')
            frontend_messages.update(
                {
                    'id':      'pendingTaskHaltedPostProcessorQueueFull',
                    'type':    'status',
                    'code':    'pendingTaskHaltedPostProcessorQueueFull',
                    'message': '',
                    'timeout': 0
                }
            )
            return True

        # Remove the status notification
        frontend_messages.remove_item('pendingTaskHaltedPostProcessorQueueFull')
        return False

    def pause_worker_thread(self, worker_id):
        """
        Pauses a single worker thread

        :param worker_id:
        :type worker_id:
        :return:
        :rtype:
        """
        if worker_id not in self.worker_threads:
            self._log("Asked to pause Worker ID '{}', but this was not found.".format(worker_id), level='warning')
            return False

        if not self.worker_threads[worker_id].is_paused():
            self._log("Asked to pause Worker ID '{}'".format(worker_id), level='debug')
            self.worker_threads[worker_id].pause()
        return True

    def pause_all_worker_threads(self, worker_group_id=None):
        """Pause all threads"""
        result = True
        for thread in self.worker_threads:
            # Limit by worker group if requested
            if worker_group_id and self.worker_threads[thread].worker_group_id != worker_group_id:
                continue
            if not self.pause_worker_thread(thread):
                result = False
        return result

    def resume_worker_thread(self, worker_id):
        """
        Resume a single worker thread

        :param worker_id:
        :type worker_id:
        :return:
        :rtype:
        """
        self._log("Asked to resume Worker ID '{}'".format(worker_id), level='debug')
        if worker_id not in self.worker_threads:
            self._log("Asked to resume Worker ID '{}', but this was not found.".format(worker_id), level='warning')
            return False

        self.worker_threads[worker_id].unpause()
        return True

    def resume_all_worker_threads(self, worker_group_id=None):
        """Resume all threads"""
        result = True
        for thread in self.worker_threads:
            # Limit by worker group if requested
            if worker_group_id and self.worker_threads[thread].worker_group_id != worker_group_id:
                continue
            if not self.resume_worker_thread(thread):
                result = False
        return result

    def terminate_worker_thread(self, worker_id):
        """
        Terminate a single worker thread

        :param worker_id:
        :type worker_id:
        :return:
        :rtype:
        """
        self._log("Asked to terminate Worker ID '{}'".format(worker_id), level='debug')
        if worker_id not in self.worker_threads:
            self._log("Asked to terminate Worker ID '{}', but this was not found.".format(worker_id), level='warning')
            return False

        self.mark_worker_thread_as_redundant(worker_id)
        return True

    def terminate_all_worker_threads(self):
        """Terminate all threads"""
        result = True
        for thread in self.worker_threads:
            if not self.terminate_worker_thread(thread):
                result = False
        return result

    def mark_worker_thread_as_redundant(self, worker_id, immediate=False):
        self.worker_threads[worker_id].set_redundant(immediate=immediate)

    def run(self):
        self._log("Starting Foreman Monitor loop")

        # TODO: update on configuration change
        self.init_worker_threads()

        if not self.validate_worker_config():
            # Pause all workers
            self.pause_all_worker_threads()

        while not self.abort_flag.is_set():
            self.scheduler.run_pending()

            # If the worker config is not valid, then pause all workers until it is
            if not self.validate_worker_config():
                # Pause all workers
                self.pause_all_worker_threads()
                self.event.wait(1)
                continue

            if self.idle_workers.acquire(timeout=15):
                # have idle workers

                if self.abort_flag.is_set():
                    break

                try:
                    task = self.pendingtasks.get(timeout=15)
                except queue.Empty:
                    self.idle_workers.release()
                    continue
                except queue.ShutDown:
                    break

                # find an idle worker for our task
                for thread in self.worker_threads.values():
                    if thread.can_accept_work():
                        thread.add_work(task)
                        break
                else:
                    # this shouldn't happen since there should be an idle worker
                    # could simply put the item back into the queue
                    # and adjust the semaphore (?)
                    pass

        self._log("Leaving Foreman Monitor loop...")


    def get_all_worker_status(self):
        all_status = []
        for worker in self.worker_threads.values():
            if worker.is_alive():
                all_status.append(worker.get_status())
        return all_status


    def get_worker_status(self, worker_id):
        result = {}
        for thread in self.worker_threads:
            if int(worker_id) == int(thread):
                result = self.worker_threads[thread].get_status()
        return result
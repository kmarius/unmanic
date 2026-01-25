#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.schemas.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     01 Aug 2021, (11:45 AM)

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
from marshmallow import Schema, fields, validate


class BaseSchema(Schema):
    class Meta:
        ordered = True


# RESPONSES
# =========

class BaseSuccessSchema(BaseSchema):
    success = fields.Boolean(
        required=True,
    )


class BaseErrorSchema(BaseSchema):
    error = fields.Str(
        required=True,
    )
    messages = fields.Dict(
        required=True,
    )
    traceback = fields.List(
        cls_or_instance=fields.Str,
        required=False,
    )


class BadRequestSchema(BaseErrorSchema):
    """STATUS_ERROR_EXTERNAL = 400"""
    error = fields.Str(
        required=True,
    )


class BadEndpointSchema(BaseSchema):
    """STATUS_ERROR_ENDPOINT_NOT_FOUND = 404"""
    error = fields.Str(
        required=True,
    )


class BadMethodSchema(BaseSchema):
    """STATUS_ERROR_METHOD_NOT_ALLOWED = 405"""
    error = fields.Str(
        required=True,
    )


class InternalErrorSchema(BaseErrorSchema):
    """STATUS_ERROR_INTERNAL = 500"""
    error = fields.Str(
        required=True,
    )


# GENERIC
# =======

class RequestTableDataSchema(BaseSchema):
    """Table request schema"""

    start = fields.Int(
        required=False,
        load_default=0,
    )
    length = fields.Int(
        required=False,
        load_default=10,
    )
    search_value = fields.Str(
        required=False,
        load_default="",
    )
    status = fields.Str(
        required=False,
        load_default="all",
    )
    after = fields.DateTime(
        required=False,
        allow_none=True,
    )
    before = fields.DateTime(
        required=False,
        allow_none=True,
    )
    order_by = fields.Str(
        required=False,
        load_default="",
    )
    order_direction = fields.Str(
        required=False,
        validate=validate.OneOf(["asc", "desc"]),
    )


class RequestTableUpdateByIdList(BaseSchema):
    """Schema for updating tables by ID"""

    id_list = fields.List(
        cls_or_instance=fields.Int,
        required=True,
        validate=validate.Length(min=1),
    )


class RequestTableUpdateByUuidList(BaseSchema):
    """Schema for updating tables by UUID"""

    uuid_list = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        validate=validate.Length(min=1),
    )


class TableRecordsSuccessSchema(BaseSchema):
    """Schema for table results"""

    recordsTotal = fields.Int(
        required=False,
    )
    recordsFiltered = fields.Int(
        required=False,
        load_default=10,
    )
    results = fields.List(
        cls_or_instance=fields.Raw,
        required=False,
    )


class RequestDatabaseItemByIdSchema(BaseSchema):
    """Schema to request a single table item given its ID"""

    id = fields.Int(
        required=True,
    )


# DOCS
# ====

class DocumentContentSuccessSchema(BaseSchema):
    """Schema for updating tables by ID"""

    content = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        validate=validate.Length(min=1),
    )


# FILEBROWSER
# ===========

class RequestDirectoryListingDataSchema(BaseSchema):
    """Schema for requesting a directory content listing"""

    current_path = fields.Str(
        load_default="/",
    )
    list_type = fields.Str(
        load_default="all",
    )


class DirectoryListingResultsSchema(BaseSchema):
    """Schema for directory listing results returned"""

    directories = fields.List(
        cls_or_instance=fields.Dict,
        required=True,
        validate=validate.Length(min=0),
    )
    files = fields.List(
        cls_or_instance=fields.Dict,
        required=True,
        validate=validate.Length(min=0),
    )


# HISTORY
# =======

class RequestHistoryTableDataSchema(RequestTableDataSchema):
    """Schema for requesting completed tasks from the table"""

    order_by = fields.Str(
        load_default="finish_time",
    )


class CompletedTasksTableResultsSchema(BaseSchema):
    """Schema for completed tasks results returned by the table"""

    id = fields.Int(
        required=True,
    )
    task_label = fields.Str(
        required=True,
    )
    task_success = fields.Boolean(
        required=True,
    )
    finish_time = fields.Int(
        required=True,
    )


class CompletedTasksSchema(TableRecordsSuccessSchema):
    """Schema for returning a list of completed task results"""

    successCount = fields.Int(
        required=True,
    )
    failedCount = fields.Int(
        required=True,
    )
    results = fields.Nested(
        CompletedTasksTableResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


class CompletedTasksLogRequestSchema(BaseSchema):
    """Schema for requesting a task log"""

    task_id = fields.Int(
        required=True,
    )


class CompletedTasksLogSchema(BaseSchema):
    """Schema for returning a list of completed task results"""

    command_log = fields.Str(
        required=True,
    )
    command_log_lines = fields.List(
        cls_or_instance=fields.Str,
        required=True,
    )


class RequestAddCompletedToPendingTasksSchema(RequestTableUpdateByIdList):
    """Schema for adding a completed task to the pending task queue"""

    library_id = fields.Int(
        required=False,
        load_default=0,
    )


# NOTIFICATIONS
# =============

class NotificationDataSchema(BaseSchema):
    """Schema for notification data"""

    uuid = fields.Str(
        required=True,
    )
    type = fields.Str(
        required=True,
    )
    icon = fields.Str(
        required=True,
    )
    label = fields.Str(
        required=True,
    )
    message = fields.Str(
        required=True,
    )
    navigation = fields.Dict(
        required=True,
    )


class RequestNotificationsDataSchema(BaseSchema):
    """Schema for returning the current list of notifications"""

    notifications = fields.Nested(
        NotificationDataSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


# PENDING
# =======

class RequestPendingTableDataSchema(RequestTableDataSchema):
    """Schema for requesting pending tasks from the table"""

    order_by = fields.Str(
        load_default="priority",
    )


class PendingTasksTableResultsSchema(BaseSchema):
    """Schema for pending task results returned by the table"""

    id = fields.Int(
        required=True,
    )
    abspath = fields.Str(
        required=True,
    )
    priority = fields.Int(
        required=True,
    )
    type = fields.Str(
        required=True,
    )
    status = fields.Str(
        required=True,
    )
    checksum = fields.Str(
        required=False,
    )
    library_id = fields.Int(
        required=False,
    )
    library_name = fields.Str(
        required=False,
    )


class PendingTasksSchema(TableRecordsSuccessSchema):
    """Schema for returning a list of pending task results"""

    results = fields.Nested(
        PendingTasksTableResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


class RequestPendingTasksReorderSchema(RequestTableUpdateByIdList):
    """Schema for moving pending items to top or bottom of table by ID"""

    position = fields.Str(
        required=True,
        validate=validate.OneOf(["top", "bottom"]),
    )


class RequestPendingTaskCreateSchema(BaseSchema):
    """Schema for requesting the creation of a pending task"""

    path = fields.Str(
        required=True,
    )
    library_id = fields.Int(
        required=False,
    )
    library_name = fields.Str(
        required=False,
    )
    type = fields.Str(
        required=False,
    )
    priority_score = fields.Int(
        required=False,
    )


class TaskDownloadLinkSchema(BaseSchema):
    """Schema for returning a download link ID"""

    link_id = fields.Str(
        required=True,
    )


class RequestPendingTasksLibraryUpdateSchema(RequestTableUpdateByIdList):
    """Schema for updating the library for a list of created tasks"""

    library_name = fields.Str(
        required=True,
    )


# PLUGINS
# =======

class RequestPluginsTableDataSchema(RequestTableDataSchema):
    """Schema for requesting plugins from the table"""

    order_by = fields.Str(
        load_default="name",
    )


class PluginStatusSchema(BaseSchema):
    installed = fields.Boolean(
        required=False,
    )
    update_available = fields.Boolean(
        required=False,
    )


class RequestPluginsByIdSchema(BaseSchema):
    """Schema to request data pertaining to a plugin by it's Plugin ID"""

    plugin_id = fields.Str(
        required=True,
    )
    repo_id = fields.Str(
        required=False,
    )


class PluginsMetadataResultsSchema(BaseSchema):
    """Schema for plugin metadata that will be returned by various requests """

    plugin_id = fields.Str(
        required=True,
    )
    name = fields.Str(
        required=True,
    )
    author = fields.Str(
        required=True,
    )
    description = fields.Str(
        required=True,
    )
    version = fields.Str(
        required=True,
    )
    icon = fields.Str(
        required=True,
    )
    tags = fields.Str(
        required=True,
    )
    status = fields.Nested(
        PluginStatusSchema,
        required=True,
    )
    changelog = fields.Str(
        required=False,
    )
    has_config = fields.Boolean(
        required=False,
    )


class PluginsTableResultsSchema(PluginsMetadataResultsSchema):
    """Schema for pending task results returned by the table"""

    id = fields.Int(
        required=True,
    )


class PluginsDataSchema(TableRecordsSuccessSchema):
    """Schema for returning a list of plugin table results"""

    results = fields.Nested(
        PluginsTableResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


class RequestPluginsInfoSchema(RequestPluginsByIdSchema):
    """Schema for requesting plugins info by a given Plugin ID"""

    prefer_local = fields.Boolean(
        required=False,
        load_default=True,
    )
    library_id = fields.Int(
        required=False,
        load_default=0,
    )


class PluginsConfigInputItemSchema(BaseSchema):
    """Schema for plugin config input items"""

    key_id = fields.Str(
        required=True,
    )
    key = fields.Str(
        required=True,
    )
    value = fields.Raw(
        required=True,
    )
    input_type = fields.Str(
        required=True,
    )
    label = fields.Str(
        required=True,
    )
    description = fields.Str(
        required=True,
        allow_none=True,
    )
    tooltip = fields.Str(
        required=True,
        allow_none=True,
    )
    select_options = fields.List(
        cls_or_instance=fields.Dict,
        required=True,
    )
    slider_options = fields.Dict(
        required=True,
    )
    display = fields.Str(
        required=True,
    )
    sub_setting = fields.Boolean(
        required=True,
    )


class PluginsInfoResultsSchema(PluginsMetadataResultsSchema):
    """Schema for pending task results returned by the table"""

    settings = fields.Nested(
        PluginsConfigInputItemSchema,
        required=False,
        many=True,
    )


class RequestPluginsSettingsSaveSchema(BaseSchema):
    """Schema for requesting the update of a plugins settings by the plugin install ID"""

    plugin_id = fields.Str(
        required=True,
    )
    settings = fields.Nested(
        PluginsConfigInputItemSchema,
        required=True,
        many=True,
    )
    library_id = fields.Int(
        required=False,
        load_default=0,
    )


class RequestPluginsSettingsResetSchema(BaseSchema):
    """Schema for requesting the reset of a plugins settings by the plugin install ID"""

    plugin_id = fields.Str(
        required=True,
    )
    library_id = fields.Int(
        required=False,
        load_default=0,
    )


class PluginsMetadataInstallableResultsSchema(PluginsMetadataResultsSchema):
    """Schema for plugin metadata that will be returned when fetching installable plugins """

    package_url = fields.Str(
        required=False,
    )
    changelog_url = fields.Str(
        required=False,
    )
    repo_name = fields.Str(
        required=False,
    )
    repo_id = fields.Str(
        required=False,
    )


class PluginsInstallableResultsSchema(BaseSchema):
    """Schema for installable plugins lists that are returned"""

    plugins = fields.Nested(
        PluginsMetadataInstallableResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


class PluginTypesResultsSchema(BaseSchema):
    """Schema for installable plugins lists that are returned"""

    results = fields.List(
        cls_or_instance=fields.Str,
        required=True,
    )


class RequestPluginsFlowByPluginTypeSchema(BaseSchema):
    """Schema to request the plugin flow of a given plugin type"""

    plugin_type = fields.Str(
        required=True,
    )
    library_id = fields.Int(
        required=False,
        load_default=1,
    )


class PluginFlowDataResultsSchema(BaseSchema):
    """Schema for plugin flow data items"""

    plugin_id = fields.Str(
        required=True,
    )
    name = fields.Str(
        required=True,
    )
    author = fields.Str(
        required=True,
    )
    description = fields.Str(
        required=True,
    )
    version = fields.Str(
        required=True,
    )
    icon = fields.Str(
        required=True,
    )


class PluginFlowResultsSchema(BaseSchema):
    """Schema for returned plugin flow list"""

    results = fields.Nested(
        PluginFlowDataResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


class RequestSavingPluginsFlowByPluginTypeSchema(RequestPluginsFlowByPluginTypeSchema):
    """Schema to request saving the plugin flow of a given plugin type"""

    plugin_flow = fields.Nested(
        PluginFlowDataResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=1),
    )
    library_id = fields.Int(
        required=False,
        load_default=1,
    )


class PluginReposMetadataResultsSchema(BaseSchema):
    """Schema for plugin repo metadata that will be returned when fetching repo lists"""

    id = fields.Str(
        required=True,
    )
    name = fields.Str(
        required=True,
    )
    icon = fields.Str(
        required=True,
    )
    path = fields.Str(
        required=True,
    )


class RequestUpdatePluginReposListSchema(BaseSchema):
    """Schema to request an update of the plugin repos list"""

    repos_list = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        validate=validate.Length(min=0),
    )


class PluginReposListResultsSchema(BaseSchema):
    """Schema for plugin repo lists that are returned"""

    repos = fields.Nested(
        PluginReposMetadataResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


class PluginsDataPanelTypesDataSchema(BaseSchema):
    """Schema for returning a list of data panel plugins results"""

    results = fields.Nested(
        PluginFlowDataResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


# SESSION
# =======

class SessionStateSuccessSchema(BaseSchema):
    """Schema for returning session data"""

    level = fields.Int(
        required=True,
    )
    picture_uri = fields.Str(
        required=False,
    )
    name = fields.Str(
        required=False,
    )
    email = fields.Str(
        required=False,
    )
    created = fields.Number(
        required=False,
    )
    uuid = fields.Str(
        required=True,
    )


# SETTINGS
# ========

class SettingsReadAndWriteSchema(BaseSchema):
    """Schema to request the current settings"""

    settings = fields.Dict(
        required=True,
    )


class SettingsSystemConfigSchema(BaseSchema):
    """Schema to display the current system configuration"""

    configuration = fields.Dict(
        required=True,
    )


class WorkerEventScheduleResultsSchema(BaseSchema):
    """Schema for worker status results"""

    repetition = fields.Str(
        required=True,
    )
    schedule_task = fields.Str(
        required=True,
    )
    schedule_time = fields.Str(
        required=True,
    )
    schedule_worker_count = fields.Int(
        required=False,
    )


class SettingsWorkerGroupConfigSchema(BaseSchema):
    """Schema to display the config of a single worker group"""

    id = fields.Int(
        required=True,
        allow_none=True,
    )
    locked = fields.Boolean(
        required=True,
    )
    name = fields.Str(
        required=True,
    )
    number_of_workers = fields.Int(
        required=True,
    )
    worker_event_schedules = fields.Nested(
        WorkerEventScheduleResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )
    tags = fields.List(
        cls_or_instance=fields.Str,
        required=True,
    )


class WorkerGroupsListSchema(BaseSchema):
    """Schema to list all worker groups"""

    worker_groups = fields.Nested(
        SettingsWorkerGroupConfigSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )


class RequestSettingsRemoteInstallationAddressValidationSchema(BaseSchema):
    """Schema to request validation of remote installation address"""

    address = fields.Str(
        required=True,
    )
    auth = fields.Str(
        required=False,
        allow_none=True,
    )
    username = fields.Str(
        required=False,
        allow_none=True,
    )
    password = fields.Str(
        required=False,
        allow_none=True,
    )


class SettingsRemoteInstallationDataSchema(BaseSchema):
    """Schema to display the data from the remote installation"""

    installation = fields.Dict(
        required=True,
    )


class RequestRemoteInstallationLinkConfigSchema(BaseSchema):
    """Schema to request a single remote installation link configuration given its UUID"""

    uuid = fields.Str(
        required=True,
    )


class SettingsRemoteInstallationLinkConfigSchema(BaseSchema):
    """Schema to display the data from the remote installation"""

    link_config = fields.Dict(
        required=True,
    )
    distributed_worker_count_target = fields.Int(
        required=False,
    )


class LibraryResultsSchema(BaseSchema):
    """Schema for library results"""

    id = fields.Int(
        required=True,
    )
    name = fields.Str(
        required=True,
    )
    path = fields.Str(
        required=True,
    )
    locked = fields.Boolean(
        required=True,
    )
    enable_remote_only = fields.Boolean(
        required=True,
    )
    enable_scanner = fields.Boolean(
        required=True,
    )
    enable_inotify = fields.Boolean(
        required=True,
    )
    tags = fields.List(
        cls_or_instance=fields.Str,
        required=True,
    )


class SettingsLibrariesListSchema(BaseSchema):
    """Schema to list all libraries"""

    libraries = fields.Nested(
        LibraryResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=1),
    )


class RequestLibraryByIdSchema(BaseSchema):
    """Schema to request a single library given its ID"""

    id = fields.Int(
        required=True,
    )


class SettingsLibraryConfigReadAndWriteSchema(BaseSchema):
    """Schema to display the data from the remote installation"""

    library_config = fields.Dict(
        required=True,
    )

    plugins = fields.Dict(
        required=False,
    )


class SettingsLibraryPluginConfigExportSchema(BaseSchema):
    """Schema for exporting a library's plugin config"""

    plugins = fields.Dict(
        required=True,
    )

    library_config = fields.Dict(
        required=False,
    )


class SettingsLibraryPluginConfigImportSchema(SettingsLibraryPluginConfigExportSchema):
    """Schema for import a library's plugin config"""

    library_id = fields.Int(
        required=True,
    )


# VERSION
# =======

class VersionReadSuccessSchema(BaseSchema):
    """Schema for returning the application version"""

    version = fields.Str(
        required=True,
    )


# WORKERS
# =======

class RequestWorkerByIdSchema(BaseSchema):
    """Schema to request a worker by the worker's ID"""

    worker_id = fields.Str(
        required=True,
    )


class WorkerStatusResultsSchema(BaseSchema):
    """Schema for worker status results"""

    id = fields.Str(
        required=True,
    )
    name = fields.Str(
        required=True,
    )
    idle = fields.Boolean(
        required=True,
    )
    paused = fields.Boolean(
        required=True,
    )
    start_time = fields.Str(
        required=True,
        allow_none=True,
    )
    current_file = fields.Str(
        required=True,
    )
    current_task = fields.Int(
        required=True,
        allow_none=True,
    )
    worker_log_tail = fields.List(
        cls_or_instance=fields.Str,
        required=True,
        validate=validate.Length(min=0),
    )
    runners_info = fields.Dict(
        required=True,
    )
    subprocess = fields.Dict(
        required=True,
    )


class WorkerStatusSuccessSchema(BaseSchema):
    """Schema for returning the status of all workers"""

    workers_status = fields.Nested(
        WorkerStatusResultsSchema,
        required=True,
        many=True,
        validate=validate.Length(min=0),
    )
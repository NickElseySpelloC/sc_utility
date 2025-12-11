"""Validation schema for YAML configuration files."""

yaml_config_validation = {
    "Files": {
        "type": "dict",
        "schema": {
            "LogfileName": {"type": "string", "required": False, "nullable": True},
            "LogfileMaxLines": {"type": "number", "required": False, "nullable": True, "min": 0, "max": 100000},
            "TimestampFormat": {"type": "string", "required": False, "nullable": True},
            "LogProcessID": {"type": "boolean", "required": False, "nullable": True},
            "LogThreadID": {"type": "boolean", "required": False, "nullable": True},
            "LogfileVerbosity": {"type": "string", "required": True, "allowed": ["none", "error", "warning", "summary", "detailed", "debug", "all"]},
            "ConsoleVerbosity": {"type": "string", "required": True, "allowed": ["error", "warning", "summary", "detailed", "debug"]},
        },
    },
    "Email": {
        "type": "dict",
        "schema": {
            "EnableEmail": {"type": "boolean", "required": False, "nullable": True},
            "SendEmailsTo": {"type": "string", "required": False, "nullable": True},
            "SMTPServer":  {"type": "string", "required": False, "nullable": True},
            "SMTPPort": {"type": "number", "required": False, "nullable": True, "min": 25, "max": 10000},
            "SMTPUsername": {"type": "string", "required": False, "nullable": True},
            "SMTPPassword": {"type": "string", "required": False, "nullable": True},
            "SubjectPrefix": {"type": "string", "required": False, "nullable": True},
        },
    },
    "ShellyDevices": {
        "type": "dict",
        "schema": {
            "AllowDebugLogging": {"type": "boolean", "required": False, "nullable": True},
            "ResponseTimeout": {"type": "number", "required": False, "nullable": True, "min": 1, "max": 120},
            "RetryCount": {"type": "number", "required": False, "nullable": True, "min": 0, "max": 10},
            "RetryDelay": {"type": "number", "required": False, "nullable": True, "min": 1, "max": 10},
            "PingAllowed": {"type": "boolean", "required": False, "nullable": True},
            "SimulationFileFolder": {"type": "string", "required": False, "nullable": True},
            "WebhooksEnabled": {"type": "boolean", "required": False, "nullable": True},
            "WebhookHost": {"type": "string", "required": False, "nullable": True},
            "WebhookPort": {"type": "number", "required": False, "nullable": True},
            "WebhookPath": {"type": "string", "required": False, "nullable": True},
            "DefaultWebhooks": {
                "type": "dict",
                "required": False,
                "nullable": True,
                "schema": {
                    "Inputs": {
                        "type": "list",
                        "required": False,
                        "nullable": True,
                        "schema": {
                            "type": "string",
                            "required": True,
                        },
                    },
                    "Outputs": {
                        "type": "list",
                        "required": False,
                        "nullable": True,
                        "schema": {
                            "type": "string",
                            "required": True,
                        },
                    },
                    "Meters": {
                        "type": "list",
                        "required": False,
                        "nullable": True,
                        "schema": {
                            "type": "string",
                            "required": True,
                        },
                    },
                },
            },
            "Devices": {
                "type": "list",
                "required": True,
                "nullable": False,
                "schema": {
                    "type": "dict",
                    "schema": {
                        "Name": {"type": "string", "required": False, "nullable": True},
                        "Model": {"type": "string", "required": True},
                        "Hostname": {"type": "string", "required": False, "nullable": True},
                        "Port": {"type": "number", "required": False, "nullable": True},
                        "ID": {"type": "number", "required": False, "nullable": True},
                        "Simulate": {"type": "boolean", "required": False, "nullable": True},
                        "ExpectOffline": {"type": "boolean", "required": False, "nullable": True},
                        "Inputs": {
                            "type": "list",
                            "required": False,
                            "nullable": True,
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "Name": {"type": "string", "required": False, "nullable": True},
                                    "ID": {"type": "number", "required": False, "nullable": True},
                                    "Webhooks": {"type": "boolean", "required": False, "nullable": True},
                                },
                            },
                        },
                        "Outputs": {
                            "type": "list",
                            "required": False,
                            "nullable": True,
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "Name": {"type": "string", "required": False, "nullable": True},
                                    "ID": {"type": "number", "required": False, "nullable": True},
                                    "Webhooks": {"type": "boolean", "required": False, "nullable": True},
                                },
                            },
                        },
                        "Meters": {
                            "type": "list",
                            "required": False,
                            "nullable": True,
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "Name": {"type": "string", "required": False, "nullable": True},
                                    "ID": {"type": "number", "required": False, "nullable": True},
                                    "MockRate": {"type": "number", "required": False, "nullable": True},
                                },
                            },
                        },
                        "TempProbes": {
                            "type": "list",
                            "required": False,
                            "nullable": True,
                            "schema": {
                                "type": "dict",
                                "schema": {
                                    "Name": {"type": "string", "required": False, "nullable": True},
                                    "ID": {"type": "number", "required": False, "nullable": True},
                                    "RequiresOutput": {"type": "string", "required": False, "nullable": True},
                                },
                            },
                        },
                    },
                },
            },
        }
    }
}
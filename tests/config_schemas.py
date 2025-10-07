"""Configuration schemas for use with the SCConfigManager class."""


class ConfigSchema:
    """Base class for configuration schemas."""

    def __init__(self):
        self.default = {
            "Files": {
                "LogfileName": "example.log",
                "LogfileMaxLines": 5000,
                "LogfileVerbosity": "summary",
                "ConsoleVerbosity": "summary",
            },
            "Email": {
                "EnableEmail": False,
                "SendEmailsTo": "<Your email address here>",
                "SMTPServer": "<Your SMTP server here>",
                "SMTPPort": 587,
                "SMTPUsername": "<Your SMTP username here>",
                "SMTPPassword": "<Your SMTP password here>",
                "SubjectPrefix": None,
            },
        }

        self.placeholders = {
            "Email": {
                "SMTPUsername": "<Your SMTP username here>",
                "SMTPPassword": "<Your SMTP password here>",
            }
        }

        self.validation = {
            "Testing": {
                "type": "dict",
                "schema": {
                    "Value1": {"type": "number", "required": True},
                    "Value2": {"type": "number", "required": True},
                    "String1": {"type": "string", "required": True},
                    "String2": {"type": "string", "required": True},
                },
            },
            "Files": {
                "type": "dict",
                "schema": {
                    "LogfileName": {"type": "string", "required": False, "nullable": True},
                    "LogfileMaxLines": {"type": "number", "required": False, "nullable": True, "min": 0, "max": 100000},
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
                    "ResponseTimeout": {"type": "number", "required": False, "nullable": True, "min": 1, "max": 120},
                    "RetryCount": {"type": "number", "required": False, "nullable": True, "min": 0, "max": 10},
                    "RetryDelay": {"type": "number", "required": False, "nullable": True, "min": 1, "max": 10},
                    "PingAllowed": {"type": "boolean", "required": False, "nullable": True},
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
                            },
                        },
                    },
                }
            },
        }

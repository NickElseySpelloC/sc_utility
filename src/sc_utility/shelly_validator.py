"""Validation schema for a ShellyDevices configuration, to be used with Cerberus."""

shelly_validator = {
    "type": "dict",
    "schema": {
        "AllowDebugLogging": {"type": "boolean", "required": False, "nullable": True},
        "ResponseTimeout": {"type": "number", "required": False, "nullable": True, "min": 1, "max": 120},
        "RetryCount": {"type": "number", "required": False, "nullable": True, "min": 0, "max": 10},
        "RetryDelay": {"type": "number", "required": False, "nullable": True, "min": 1, "max": 10},
        "PingAllowed": {"type": "boolean", "required": False, "nullable": True},
        "MaxConcurrentErrors": {"type": "number", "required": False, "nullable": True, "min": 0},
        "WebhooksEnabled": {"type": "boolean", "required": False, "nullable": True},
        "WebhookHost": {"type": "string", "required": False, "nullable": True},
        "WebhookPort": {"type": "number", "required": False, "nullable": True},
        "WebhookPath": {"type": "string", "required": False, "nullable": True},
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
                                "Group": {"type": "string", "required": False, "nullable": True},
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
                            },
                        },
                    },
                },
            },
        },
    }
}

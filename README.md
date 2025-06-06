# Spello Consulting Utility Library

A Python utility library for log file management and YAML configuration file management 

Details to follow 

## Example code

    import sys

    from config_schemas import ConfigSchema
    from sc_utility import SCConfigManager, SCLogger

    CONFIG_FILE = "config.yaml"


    def main():
        print("Hello from sc-utility!")

        # Get our default schema, validation schema, and placeholders
        schemas = ConfigSchema()

        # Initialize the SC_ConfigManager class
        try:
            config = SCConfigManager(
                config_file=CONFIG_FILE,
                default_config=schemas.default,  # Replace with your default config if needed
                validation_schema=schemas.validation,  # Replace with your validation schema if needed
                placeholders=schemas.placeholders  # Replace with your placeholders if needed
            )
        except RuntimeError as e:
            print(f"Configuration file error: {e}", file=sys.stderr)
            return

        config_value = config.get("AmberAPI", "APIKey", default="this is the default value")
        if config_value is None:
            print("Configuration value not found")
        else:
            print(f"Configuration loaded successfully. Sample value: {config_value}")

        # Initialize the SC_Logger class
        try:
            logger = SCLogger(config.get_logger_settings())
        except RuntimeError as e:
            print(f"Logger initialisation error: {e}", file=sys.stderr)
            return

        logger.log_message("This is a test message at the debug level.", "debug")
        # logger.log_message("This is a test message at the error level.", "error")

        # Setup email
        email_settings = config.get_email_settings()
        logger.register_email_settings(email_settings)

        if logger.send_email("Hello world", "This is a test email from the sc-utility test harness."):
            logger.log_message("Email sent OK.", "detailed")

        if logger.get_fatal_error():
            print("Prior fatal error detected.")
            logger.clear_fatal_error()

        # logger.log_fatal_error("This is a test fatal error message.")

        logger.clear_fatal_error()

    if __name__ == "__main__":
        main()



## Exceptions 

The initialisation functions throw RuntimeError exceptions if a fatal error is encountered. 
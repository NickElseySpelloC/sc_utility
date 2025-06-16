# Spello Consulting Utility Library

A Python utility library for log file management and YAML configuration file management. 

# Example code

    import sys

    from config_schemas import ConfigSchema
    from sc_utility import SCConfigManager, SCLogger

    CONFIG_FILE = "config.yaml"
    EXCEL_FILE = "sample_excel.xlsx"

    def main():
        """Main function to run the example code."""
        print(f"Hello from sc-utility! running on {platform.system()}")

        # Get our config schema, validation schema, and placeholders
        schemas = ConfigSchema()

        # Initialize the SCConfigManager class
        try:
            config = SCConfigManager(
                config_file=CONFIG_FILE,
                default_config=schemas.default,
                validation_schema=schemas.validation,
                placeholders=schemas.placeholders
            )
        except RuntimeError as e:
            print(f"Configuration file error: {e}", file=sys.stderr)
            return

        # Get some parameteer from the config file
        print(f"API key = {config.get('AmberAPI', 'APIKey')}")

        # Initialize the SCLogger class
        try:
            logger = SCLogger(config.get_logger_settings())
        except RuntimeError as e:
            print(f"Logger initialisation error: {e}", file=sys.stderr)
            return

        # Log a message to the log file
        logger.log_message("This is a test message at the debug level.", "debug")

        # Setup email
        email_settings = config.get_email_settings()
        logger.register_email_settings(email_settings)

        text_msg = "Hello world from the sc_utility library."
        if logger.send_email("Hello world", text_msg):
            logger.log_message("Email sent OK.", "detailed")

        # Test the ExcelReader class
        excel_reader = ExcelReader(EXCEL_FILE)
        try:
            table_data = excel_reader.extract_data(source_name="Table1", source_type="table")
            print(f"Extracted table data: {table_data}")
        except ImportError as e:
            logger.log_fatal_error(f"Error extracting table: {e}")

        # See if there was a fatal error during a prior run. 
        if logger.get_fatal_error():
            print("Prior fatal error detected.")
            logger.clear_fatal_error()

    if __name__ == "__main__":
        main()


# Configuration File 
The library uses a YAML file for configuration. An example of included with the project (*config.yaml.example*). Copy this to *your_app.yaml* before using the library. Here's an example config file - the library expects to find the Files and Email sections in the file:

    # Just an example section to show how to set up a section
    AmberAPI:
        APIKey: somerandomkey342
        BaseUrl: https://api.amber.com.au/v1
        Timeout: 15
    
    Files:
        LogfileName: logfile.log
        LogfileMaxLines: 500
        LogfileVerbosity: detailed
        ConsoleVerbosity: detailed

    Email:
        EnableEmail: True
        SMTPServer: smtp.gmail.com
        SMTPPort: 587
        SMTPUsername: me@gmail.com
        SMTPPassword: <Your SMTP password>
        SubjectPrefix: "[Bob Portfolio]: "


## Configuration Parameters

### Section: Files

| Parameter | Description | 
|:--|:--|
| LogfileName | The name of the log file, can be a relative or absolute path. | 
| LogfileMaxLines | Maximum number of lines to keep in the log file. If zero, file will never be truncated. | 
| LogfileVerbosity | The level of detail captured in the log file. One of: none; error; warning; summary; detailed; debug; all | 
| ConsoleVerbosity | Controls the amount of information written to the console. One of: error; warning; summary; detailed; debug; all. Errors are written to stderr all other messages are written to stdout | 

### Section: Email

| Parameter | Description | 
|:--|:--|
| EnableEmail | Set to *True* if you want to allow the app to send emails. If True, the remaining settings in this section must be configured correctly. | 
| SMTPServer | The SMTP host name that supports TLS encryption. If using a Google account, set to smtp.gmail.com |
| SMTPPort | The port number to use to connect to the SMTP server. If using a Google account, set to 587 |
| SMTPUsername | Your username used to login to the SMTP server. If using a Google account, set to your Google email address. |
| SMTPPassword | The password used to login to the SMTP server. If using a Google account, create an app password for the app at https://myaccount.google.com/apppasswords  |
| SubjectPrefix | Optional. If set, the app will add this text to the start of any email subject line for emails it sends. |

# Library reference 
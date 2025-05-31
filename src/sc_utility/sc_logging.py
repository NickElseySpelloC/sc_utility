"""
Spello Consulting Logging Module.

Provides general purpose logging functions.
"""

import inspect
import smtplib
import sys
import traceback
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


class SCLogger:
    """A class to handle logging messages with different verbosity levels."""

    def __init__(self, logger_settings: dict | None = None, logfile_name: str | None = None, file_verbosity: str | None = "detailed", console_verbosity: str | None = "summary", max_lines: int | None = 10000):
        """
        Initializes the logger with configuration settings.

        param logger_settings: A dictionary containing logger settings. If provided, it should include the same keys as the individual parameters below:

        param logfile_name: str, the name of the log file (optional, defaults to None)
        param file_verbosity: str, verbosity level for file logging (optional, defaults to "detailed")
        param console_verbosity: str, verbosity level for console logging (optional, defaults to "summary")
        param max_lines: int, maximum number of lines to keep in the log file (optional, defaults to 10000)
        If logger_settings is provided, it will override the individual parameters.
        """
        if logger_settings is not None:
            self.logfile_name = logger_settings["logfile_name"]
            self.file_verbosity = logger_settings["file_verbosity"]
            self.console_verbosity= logger_settings["console_verbosity"]
            self.max_lines = logger_settings["max_lines"]
        else:
            self.logfile_name = logfile_name
            self.file_verbosity = file_verbosity
            self.console_verbosity= console_verbosity
            self.max_lines = max_lines

        self.verbosity_levels = {
            "none": 0,
            "error": 1,
            "warning": 2,
            "summary": 3,
            "detailed": 4,
            "debug": 5,
            "all": 6,
        }

        # Use the register_email_settings method to set up email settings
        self.email_settings = None

        # See if logfile writing is required
        self.file_logging_enabled = self.logfile_name is not None

        # Make a note of the app directory
        self.app_dir = Path(__file__).parent

        if self.file_logging_enabled:
            # Determine the file path for the log file
            current_dir = Path.cwd()

            self.logfile_path = current_dir / self.logfile_name
            if not self.logfile_path.exists():
                self.logfile_path = self.app_dir / self.logfile_name

            # Truncate the log file if it exists
            self._initialise_monitoring_logfile()

        # Setup the path to the fatal error tracking file
        self.fatal_error_file_path = self.app_dir / f"{self.app_dir.name}_fatal_error.txt"


    def _initialise_monitoring_logfile(self) -> None:
        """Initialise the monitoring log file. If it exists, truncate it to the max number of lines."""
        if not self.file_logging_enabled:
            return

        if Path(self.logfile_path).exists():
            # Monitoring log file exists - truncate excess lines if needed.
            with Path(self.logfile_path).open(encoding="utf-8") as file:

                if self.max_lines > 0:
                    lines = file.readlines()

                    if len(lines) > self.max_lines:
                        # Keep the last max_lines rows
                        keep_lines = lines[-self.max_lines:] if len(lines) > self.max_lines else lines

                        # Overwrite the file with only the last 1000 lines
                        with Path(self.logfile_path).open("w", encoding="utf-8") as file2:
                            file2.writelines(keep_lines)

    def log_message(self, message: str, verbosity: str = "summary") -> None:
        """Writes a log message to the console and/or a file based on verbosity settings."""
        if verbosity not in self.verbosity_levels:
            exception_msg = f"log_message(): Invalid verbosity passed, must be one of {list(self.verbosity_levels.keys())}."
            raise ValueError(exception_msg)

        logfile_level = self.verbosity_levels.get(self.file_verbosity, 0)
        console_level = self.verbosity_levels.get(self.console_verbosity, 0)
        message_level = self.verbosity_levels.get(verbosity, 0)

        # Deal with console message first
        if console_level >= message_level and console_level > 0:
            if verbosity == "error":
                print("ERROR: " + message, file=sys.stderr)
            elif verbosity == "warning":
                print("WARNING: " + message)
            else:
                print(message)

        # Now write to the log file if needed
        if self.file_logging_enabled:
            error_str = " ERROR" if verbosity == "error" else " WARNING" if verbosity == "warning" else ""
            if logfile_level >= message_level and logfile_level > 0:
                with Path(self.logfile_path).open("a", encoding="utf-8") as file:
                    if message == "":
                        file.write("\n")
                    else:
                        # Use the local timezone for the log timestamp
                        local_tz = datetime.now().astimezone().tzinfo
                        file.write(f"{datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')}{error_str}: {message}\n")

    def register_email_settings(self, email_settings: dict | None) -> None:
        """
        Registers email settings for sending emails.

        param email_settings: A dictionary object containing email settings. Keys should include:
            - SendEmailsTo: str, the email address to send emails to
            - SMTPServer: str, the SMTP server address
            - SMTPPort: int, the SMTP server port (optional, defaults to 587)
            - SMTPUsername: str, the username for the SMTP server
            - SMTPPassword: str, the password for the SMTP server (preferably an App Password)
            - SubjectPrefix: str, a prefix for email subjects (optional, default to None)
        """
        if email_settings == {} or email_settings is None:
            return  # No email settings provided, so skip registration

        if not isinstance(email_settings, dict):
            msg = "register_email_settings(): Email settings must be a dictionary."
            raise TypeError(msg)

        # Check if all required keys are present
        required_keys = ["SendEmailsTo", "SMTPServer", "SMTPUsername", "SMTPPassword"]
        for key in required_keys:
            if key not in email_settings:
                msg = f"register_email_settings(): Missing required email setting: {key}"
                raise ValueError(msg)

        # Store the email settings in the config object
        self.email_settings = email_settings

    def send_email(self, subject: str, body: str) -> bool:
        """Sends an email using the SMTP server previously specified in register_email_settings()."""
        if self.email_settings is None:
            return False # No email settings registered, so skip sending the email

        # Load the Gmail SMTP server configuration
        sender_email = self.email_settings.get("SMTPUsername")
        send_to = self.email_settings.get("SendEmailsTo")

        try:
            # Create the email
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = send_to
            if self.email_settings.get("SubjectPrefix", None) is not None:
                msg["Subject"] = self.email_settings.get("SubjectPrefix") + subject
            else:
                msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            # Connect to the Gmail SMTP server
            with smtplib.SMTP(self.email_settings.get("SMTPServer"), self.email_settings.get("SMTPPort", 587)) as server:
                server.starttls()  # Upgrade the connection to secure
                server.login(sender_email, self.email_settings.get("SMTPPassword"))  # Log in using App Password
                server.sendmail(sender_email, send_to, msg.as_string())  # Send the email

        except RuntimeError as e:
            self.log_fatal_error(f"send_email(): Failed to send email with subject {msg['Subject']}: {e}")
            return False

        else:
            return True  # Email sent successfully

    def log_fatal_error(self, message: str, report_stack: bool=False, calling_function: str | None=None) -> None:  # noqa: FBT001, FBT002
        """
        Log a fatal error, send an email if configured to so and then exit the program.

        param message: The error message to log.
        param report_stack: If True, include the stack trace in the log message.
        param calling_function: The name of the function that called this method, if known. If None, the calling function will be determined automatically.
        """
        function_name = None
        if calling_function is None:
            stack = inspect.stack()
            # Get the frame of the calling function
            calling_frame = stack[1]
            # Get the function name
            function_name = calling_frame.function
            if function_name == "<module>":
                function_name = "main"
            # Get the class name (if it exists)
            class_name = None
            if "self" in calling_frame.frame.f_locals:
                class_name = calling_frame.frame.f_locals["self"].__class__.__name__
                full_reference = f"{class_name}.{function_name}()"
            else:
                full_reference = function_name + "()"
        else:
            full_reference = calling_function + "()"

        if report_stack:
            stack_trace = traceback.format_exc()
            message += f"\n\nStack trace:\n{stack_trace}"

        self.log_message(f"Function {full_reference}: FATAL ERROR: {message}", "error")

        # Try to send an email if configured to do so and we haven't already sent one for a fatal error
        # Don't send concurrent error emails
        if function_name != "send_email" and not self.get_fatal_error():
            self.send_email(
                f"{self.app_dir.name} terminated with a fatal error",
                f"{message} \nAdditional emails will not be sent for concurrent errors.",
            )

        # record the error in in a file so that we keep track of this next time round
        self.set_fatal_error(message)

        # Exit the program
        sys.exit(1)


    def get_fatal_error(self) -> bool:
        """Returns True if a fatal error was previously reported, false otherwise."""
        return Path(self.fatal_error_file_path).exists()

    def clear_fatal_error(self) -> bool:
        """
        Clear a previously logged fatal error.

        Returns True if the file was deleted, False if it did not exist.
        """
        if Path(self.fatal_error_file_path).exists():
            Path(self.fatal_error_file_path).unlink()
            return True
        return False

    def set_fatal_error(self, message: str) -> None:
        """Create a fatal error tracking file and write the message to it."""
        with Path(self.fatal_error_file_path).open("w", encoding="utf-8") as file:
            file.write(message)





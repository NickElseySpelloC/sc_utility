"""
Spello Consulting Logging Module.

Provides general purpose logging functions.
"""

import inspect
import os
import platform
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

        If logger_settings are provided, it will override the individual parameters.

        Args:
            logger_settings (Optional[dict], optional): A dictionary containing logger settings. If provided, it should include the same keys as the individual parameters below:
            logfile_name (Optional[str], optional): The name of the log file. If None, no file logging will be done.
            file_verbosity (Optional[str], optional): Verbosity level for file logging
            console_verbosity  (Optional[str], optional): Verbosity level for console logging
            max_lines  (Optional[int], optional): Maximum number of lines to keep in the log file
        """
        if logger_settings is not None:
            self.logfile_name = logger_settings["logfile_name"]
            self.file_verbosity = logger_settings["file_verbosity"]
            self.console_verbosity = logger_settings["console_verbosity"]
            self.max_lines = logger_settings["max_lines"]
            self.log_process_id = logger_settings["log_process_id"]
        else:
            self.logfile_name = logfile_name
            self.file_verbosity = file_verbosity
            self.console_verbosity = console_verbosity
            self.max_lines = max_lines
            self.log_process_id = False

        self.verbosity_levels = {
            "none": 0,
            "error": 1,
            "warning": 2,
            "summary": 3,
            "detailed": 4,
            "debug": 5,
            "all": 6,
        }

        # Platform specific settings
        self.os_name = self.get_os()

        # Use the register_email_settings method to set up email settings
        self.email_settings = None

        # See if logfile writing is required
        self.file_logging_enabled = self.logfile_name is not None

        # Make a note of the app directory
        self.app_dir = self.client_dir = Path(sys.argv[0]).parent.resolve()

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

        # Save process ID
        self.process_id = os.getpid()

    def get_os(self) -> str:  # noqa: PLR6301
        """Returns the name of the operating system.

        Returns:
            os_string (str): The name of the operating system in lowercase.
        """
        # Get the platform name and convert it to lowercase
        platform_name = platform.system().lower()

        if platform_name == "darwin":
            platform_name = "macos"

        return platform_name

    def _initialise_monitoring_logfile(self) -> None:
        """Initialise the monitoring log file. If it exists, truncate it to the max number of lines."""
        if not self.file_logging_enabled:
            return

        self.trim_logfile()

    def trim_logfile(self) -> None:
        """Trims the log file to the maximum number of lines specified."""
        if not self.file_logging_enabled:
            return

        if self.logfile_path.exists() and self.max_lines > 0:
            # Monitoring log file exists - truncate excess lines if needed.
            with self.logfile_path.open(encoding="utf-8") as file:
                lines = file.readlines()

                if len(lines) > self.max_lines:
                    # Keep the last max_lines rows
                    keep_lines = lines[-self.max_lines:] if len(lines) > self.max_lines else lines

                    # Overwrite the file with only the last 1000 lines
                    with self.logfile_path.open("w", encoding="utf-8") as file2:
                        file2.writelines(keep_lines)

    def log_message(self, message: str, verbosity: str = "summary") -> None:
        """Writes a log message to the console and/or a file based on verbosity settings.

        Args:
            message (str): The message to log.
            verbosity (str): The verbosity level for the message. Must be one of "none", "error", "warning", "summary", "detailed", "debug", or "all".

        Raises:
            ValueError: If an invalid verbosity level is provided.

        """
        if verbosity not in self.verbosity_levels:
            exception_msg = f"log_message(): Invalid verbosity passed, must be one of {list(self.verbosity_levels.keys())}."
            raise ValueError(exception_msg)

        logfile_level = self.verbosity_levels.get(self.file_verbosity, 0)
        console_level = self.verbosity_levels.get(self.console_verbosity, 0)
        message_level = self.verbosity_levels.get(verbosity, 0)

        process_str = ""
        if self.log_process_id:
            process_str = f" Proc {self.process_id}"

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
                with self.logfile_path.open("a", encoding="utf-8") as file:
                    if not message:
                        file.write("\n")
                    else:
                        # Use the local timezone for the log timestamp
                        local_tz = datetime.now().astimezone().tzinfo
                        file.write(f"{datetime.now(local_tz).strftime('%Y-%m-%d %H:%M:%S')}{process_str}{error_str}: {message}\n")

    def register_email_settings(self, email_settings: dict | None) -> None:
        """
        Registers email settings for sending emails.

        Use the SCConfigManager.get_email_settings() method to get a dictionary containing the email settings. Otherwise, you can pass a
        dictionary directly to this method with these keys:
            SendEmailsTo: str, the email address to send emails to
            SMTPServer: str, the SMTP server address
            SMTPPort: int, the SMTP server port (optional, defaults to 587)
            SMTPUsername: str, the username for the SMTP server
            SMTPPassword: str, the password for the SMTP server (preferably an App Password)
            SubjectPrefix: str, a prefix for email subjects (optional, default to None)

        Args:
            email_settings (Optional[dict], optional): A dictionary containing email settings. If empty or None, no email settings will be registered.

        Raises:
            TypeError: If email_settings is not a dictionary.
            ValueError: If any required keys are missing from the email_settings dictionary.

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

    def is_probable_path(self, possible_path: str | Path) -> bool:
        """
        Checks if the given string or Path object is likely to be a file path.

        This method checks if the string is an absolute path, contains a path separator, or has a file extension.

        Args:
            possible_path (str): The string to check.

        Returns:
            result (bool): True if the string is likely a file path, False otherwise.
        """
        max_path = 260 if self.os_name == "windows" else os.pathconf("/", "PC_PATH_MAX")

        path_obj = None
        if isinstance(possible_path, Path):
            path_str = str(possible_path)
            path_obj = possible_path
        else:
            path_str = possible_path

        if len(path_str) > max_path:
            # If the path is longer than the maximum allowed path length, it cannot be a valid path
            return False

        if path_obj is None:
            path_obj = Path(possible_path)

        # Check if it's absolute, or contains a path separator, or has a file extension
        return (
            path_obj.is_absolute() or
            "/" in path_str or "\\" in path_str or
            (path_obj.suffix.lower() is not None and path_obj.suffix.lower())
        )

    def select_file_location(self, file_name: str) -> Path:
        """
        Selects the file location for the given file name.

        Args:
            file_name (str): The name of the file to locate. Can be just a file name, or a relative or absolute path.

        Returns:
            location (Path): The full path to the file as a Path object. If the file does not exist in the current directory, it will look in the script directory.
        """
        # Look at the file_name and see if it looks like a path
        if not self.is_probable_path(file_name):
            return None

        # Check to see if file_name is a full path or just a file name
        file_path = Path(file_name)

        # Check if file_name is an absolute path, return this even if it does not exist
        if file_path.is_absolute():
            return file_path

        # Check if file_name contains any parent directories (i.e., is a relative path)
        # If so, return this even if it does not exist
        if file_path.parent != Path("."):  # noqa: PTH201
            # It's a relative path
            return (Path.cwd() / file_path).resolve()

        # Otherwise, assume it's just a file name and look for it in the current directory and the script directory
        current_dir = Path.cwd()
        app_dir = self.client_dir = Path(sys.argv[0]).parent.resolve()
        file_path = current_dir / file_name
        if not file_path.exists():
            file_path = app_dir / file_name
        return file_path

    def send_email(self, subject: str, body: str) -> bool:  # noqa: PLR0912
        """
        Sends an email using the SMTP server previously specified in register_email_settings().

        Args:
            subject (str): The subject of the email.
            body (str): The body of the email. This argument can be one of 4 things:
                1. A string containing the HTML body of the email
                2. A string containing the path to an HTML file to read the body from
                3. A string containing the text body of the email
                4. A string containing the path to an text file to read the body from

        Returns:
            result (bool): True if the email was sent successfully, False otherwise.
        """
        if self.email_settings is None:
            return False  # No email settings registered, so skip sending the email

        # First confirm that the body argument was passed as a string
        if not isinstance(body, str) and not isinstance(body, Path):
            self.log_fatal_error("body argument must be a string containing the body content or a file path.")
            return False

        # See if the body string is something that looks like a file path
        try:
            payload_path = self.select_file_location(body)
        except OSError:
            # Nothing to do here
            payload_path = None

        payload = body  # Default to the body as text content
        payload_type = "plain"

        # Default to treating the body a file path and see if we can resolve it
        if payload_path is not None:
            if payload_path.exists():
                # If the body is a file path, read the content
                with payload_path.open("r", encoding="utf-8") as file:
                    payload = file.read()

                # Determine the payload type based on the file extension
                if payload_path.suffix.lower() == ".html":
                    payload_type = "html"
                elif payload_path.suffix.lower() == ".txt":
                    payload_type = "plain"
                else:
                    self.log_fatal_error(f"Unsupported file type for email body: {payload_path.suffix}")
                    return False
            else:
                payload_path = None

        if payload_path is None:
            # If fall through to here, then the body was not a file path or the file did not exist
            # Assume that the body is a string containing the content
            payload = body  # Default to the body as text content
            if body.startswith(("<html", "<!DOCTYPE html")):
                payload_type = "html"
            else:
                payload_type = "plain"

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

            # Attach the payload as either plain text or HTML
            part = MIMEText(payload, payload_type)
            msg.attach(part)

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

    def log_fatal_error(self, message: str, report_stack: bool = False, calling_function: str | None = None) -> None:  # noqa: FBT001, FBT002
        """
        Log a fatal error, send an email if configured to so and then exit the program.

        Args:
            message (str): The error message to log.
            report_stack (Optional[bool], optional): If True, include the stack trace in the log message.
            calling_function (Optional[str], optional): The name of the function that called this method, if known. If None, the calling function will be determined automatically.

        Raises:
            SystemExit: Exits the program with a status code of 1 after logging the fatal error.

        """  # noqa: DOC502
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

        Returns:
            result (bool): True if the file was deleted, False if it did not exist.
        """
        if Path(self.fatal_error_file_path).exists():
            Path(self.fatal_error_file_path).unlink()
            return True
        return False

    def set_fatal_error(self, message: str) -> None:
        """
        Create a fatal error tracking file and write the message to it.

        Args:
            message (str): The error message to write to the fatal error file.
        """
        with Path(self.fatal_error_file_path).open("w", encoding="utf-8") as file:
            file.write(message)

    def get_process_id(self) -> int:
        """
        Returns the process ID of the current process.

        Returns:
            process_id (int): The process ID of the current process.
        """
        return self.process_id

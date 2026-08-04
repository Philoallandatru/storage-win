"""
Utility Functions for MLPerf Storage Benchmarks.

This module provides shared utility functions used throughout the mlpstorage_py
framework, including:

- JSON encoding with custom type handling
- Configuration file loading and manipulation
- Dictionary operations (nesting, flattening, updates)
- Command execution with signal handling
- MPI command generation

Classes:
    MLPSJsonEncoder: Custom JSON encoder for mlpstorage_py types.
    CommandExecutor: Execute shell commands with live output streaming.

Functions:
    read_config_from_file: Load YAML configuration files.
    generate_mpi_prefix_cmd: Generate MPI command prefix for distributed execution.
    update_nested_dict: Recursively merge two dictionaries.
    create_nested_dict: Convert flat dotted keys to nested dictionary.
    flatten_nested_dict: Convert nested dictionary to flat dotted keys.
"""

import concurrent.futures
import enum
import io
import json
import logging
import math
import os
import pprint
import psutil
import subprocess
import shlex
import select
import signal
import sys
import threading
import yaml
import ctypes
from datetime import datetime
from typing import Any, List, Union, Optional, Dict, Tuple, Set

from mlpstorage_py.config import CONFIGS_ROOT_DIR, MPIRUN, MPIEXEC, MPI_RUN_BIN, MPI_EXEC_BIN


class MLPSJsonEncoder(json.JSONEncoder):
    """Custom JSON encoder for mlpstorage_py types.

    Handles serialization of special types that the standard JSON encoder
    cannot process:
    - Sets are converted to lists
    - Enums are converted to their values
    - Logger objects are converted to placeholder strings
    - ClusterInformation objects use their .info property
    - Objects with __dict__ are serialized as dictionaries

    Example:
        >>> import json
        >>> data = {'status': PARAM_VALIDATION.CLOSED, 'hosts': {'a', 'b'}}
        >>> json.dumps(data, cls=MLPSJsonEncoder)
        '{"status": "closed", "hosts": ["a", "b"]}'
    """

    def default(self, obj: Any) -> Any:
        """Convert special types to JSON-serializable forms.

        Args:
            obj: Object to serialize.

        Returns:
            JSON-serializable representation of the object.
        """
        try:
            if isinstance(obj, (float, int, str, list, tuple, dict)):
                return super().default(obj)
            if isinstance(obj, set):
                return list(obj)
            elif "Logger" in str(type(obj)):
                return "Logger object"
            elif 'ClusterInformation' in str(type(obj)):
                return obj.info
            elif isinstance(obj, enum.Enum):
                return obj.value
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return super().default(obj)
        except Exception as e:
            return str(obj)


def is_valid_datetime_format(datetime_str: str) -> bool:
    """Check if a string is a valid datetime in the format "YYYYMMDD_HHMMSS".

    Args:
        datetime_str: String to validate.

    Returns:
        True if the string matches the datetime format, False otherwise.

    Example:
        >>> is_valid_datetime_format("20250115_143022")
        True
        >>> is_valid_datetime_format("invalid")
        False
    """
    try:
        if len(datetime_str) != 15 or datetime_str[8] != '_':
            return False
        datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")
        return True
    except ValueError:
        return False


def get_datetime_from_timestamp(datetime_str: str) -> Optional[datetime]:
    """Parse a datetime string in YYYYMMDD_HHMMSS format.

    Args:
        datetime_str: String in "YYYYMMDD_HHMMSS" format.

    Returns:
        datetime object if valid, None otherwise.

    Example:
        >>> get_datetime_from_timestamp("20250115_143022")
        datetime.datetime(2025, 1, 15, 14, 30, 22)
    """
    if is_valid_datetime_format(datetime_str):
        return datetime.strptime(datetime_str, "%Y%m%d_%H%M%S")
    return None


def read_config_from_file(relative_path: str) -> Dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        relative_path: Path relative to CONFIGS_ROOT_DIR.

    Returns:
        Dictionary containing the parsed YAML configuration.

    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        yaml.YAMLError: If the file contains invalid YAML.

    Example:
        >>> config = read_config_from_file("workloads/unet3d_h100.yaml")
        >>> config['model']['name']
        'unet3d'
    """
    config_path = os.path.join(CONFIGS_ROOT_DIR, relative_path)
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def update_nested_dict(
    original_dict: Dict[str, Any],
    update_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """Recursively merge two nested dictionaries.

    Values from update_dict override values in original_dict. Nested
    dictionaries are merged recursively rather than replaced.

    Args:
        original_dict: Base dictionary to update.
        update_dict: Dictionary with values to merge in.

    Returns:
        New dictionary with merged values.

    Example:
        >>> original = {'a': 1, 'b': {'c': 2, 'd': 3}}
        >>> update = {'b': {'c': 4}}
        >>> update_nested_dict(original, update)
        {'a': 1, 'b': {'c': 4, 'd': 3}}
    """
    updated_dict: Dict[str, Any] = {}
    for key, value in original_dict.items():
        if key in update_dict:
            if isinstance(value, dict) and isinstance(update_dict[key], dict):
                updated_dict[key] = update_nested_dict(value, update_dict[key])
            else:
                updated_dict[key] = update_dict[key]
        else:
            updated_dict[key] = value
    for key, value in update_dict.items():
        if key not in original_dict:
            updated_dict[key] = value
    return updated_dict


def create_nested_dict(
    flat_dict: Dict[str, Any],
    parent_dict: Optional[Dict[str, Any]] = None,
    separator: str = '.'
) -> Dict[str, Any]:
    """Convert a flat dictionary with dotted keys to a nested structure.

    Args:
        flat_dict: Dictionary with dotted keys (e.g., "a.b.c").
        parent_dict: Optional existing dictionary to merge into.
        separator: Character used to separate key levels.

    Returns:
        Nested dictionary structure.

    Example:
        >>> flat = {'a.b.c': 1, 'a.b.d': 2, 'e': 3}
        >>> create_nested_dict(flat)
        {'a': {'b': {'c': 1, 'd': 2}}, 'e': 3}
    """
    if parent_dict is None:
        parent_dict = {}

    for key, value in flat_dict.items():
        keys = key.split(separator)
        current_dict = parent_dict
        for i, k in enumerate(keys[:-1]):
            if k not in current_dict:
                current_dict[k] = {}
            current_dict = current_dict[k]
        current_dict[keys[-1]] = value

    return parent_dict


def flatten_nested_dict(nested_dict, parent_key='', separator='.'):
    """
    Flatten a nested dictionary structure into a single-level dictionary with keys
    joined by a separator.

    Example:
        Input: {'a': 1, 'b': {'c': 2, 'd': {'e': 3}}}
        Output: {'a': 1, 'b.c': 2, 'b.d.e': 3}

    Args:
        nested_dict (dict): The nested dictionary to flatten
        parent_key (str): The parent key prefix (used in recursion)
        separator (str): The character to use for joining keys

    Returns:
        dict: A flattened dictionary with compound keys
    """
    flat_dict = {}

    for key, value in nested_dict.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key

        if isinstance(value, dict):
            # Recursively flatten any nested dictionaries
            flat_dict.update(flatten_nested_dict(value, new_key, separator))
        else:
            # Add the leaf value to our flattened dictionary
            flat_dict[new_key] = value

    return flat_dict


def remove_nan_values(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Remove any NaN values from a dictionary.

    Useful for cleaning up metrics dictionaries before JSON serialization,
    as JSON doesn't support NaN values.

    Args:
        input_dict: Dictionary that may contain NaN float values.

    Returns:
        New dictionary with NaN values removed.

    Example:
        >>> import math
        >>> d = {'valid': 1.5, 'invalid': float('nan'), 'other': 'text'}
        >>> remove_nan_values(d)
        {'valid': 1.5, 'other': 'text'}
    """
    ret_dict: Dict[str, Any] = {}
    for k, v in input_dict.items():
        if isinstance(v, (float, int)):
            try:
                if math.isnan(v):
                    continue
            except (TypeError, ValueError):
                pass
        ret_dict[k] = v

    return ret_dict


def _split_command(command: str) -> List[str]:
    """Split a command line using the native parser for the host platform."""
    if os.name != "nt":
        return shlex.split(command)

    # CommandLineToArgvW handles quoted paths, embedded spaces, and the
    # backslash rules used by CreateProcess.  This is more faithful than
    # ``shlex.split(..., posix=False)`` which leaves quote characters in the
    # resulting tokens and still splits unquoted Windows paths at spaces.
    try:
        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32
        shell32.CommandLineToArgvW.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
        shell32.CommandLineToArgvW.restype = ctypes.POINTER(ctypes.c_wchar_p)
        argc = ctypes.c_int()
        argv = shell32.CommandLineToArgvW(command, ctypes.byref(argc))
        if not argv:
            raise ctypes.WinError()
        try:
            return [argv[index] for index in range(argc.value)]
        finally:
            kernel32.LocalFree(argv)
    except (AttributeError, OSError):
        # Keep a useful fallback for embedded Python builds without shell32.
        return [token.strip('"') for token in shlex.split(command, posix=False)]


def quote_command_token(value: Any) -> str:
    """Quote one command-line token using the host platform's conventions."""
    value = str(value)
    if os.name == "nt":
        return subprocess.list2cmdline([value])
    return value


class CommandExecutor:
    """
    A class to execute shell commands in a subprocess with live output streaming and signal handling.
    
    This class allows:
    - Executing commands as a string or list of arguments
    - Capturing stdout and stderr
    - Optionally printing stdout and stderr in real-time
    - Handling signals to gracefully terminate the process
    """
    
    def __init__(self, logger: logging.Logger, debug: bool = False):
        """
        Initialize the CommandExecutor.
        
        Args:
            debug: If True, enables debug mode with additional logging
        """
        self.logger = logger
        self.debug = debug
        self.process = None
        self.terminated_by_signal = False
        self.signal_received = None
        self._original_handlers = {}
        self._stop_event = threading.Event()
    
    def execute(self, 
                command: Union[str, List[str]], 
                print_stdout: bool = False,
                print_stderr: bool = False,
                watch_signals: Optional[Set[int]] = None) -> Tuple[str, str, int]:
        """
        Execute a command and return its stdout, stderr, and return code.
        
        Args:
            command: The command to execute (string or list of strings)
            print_stdout: If True, prints stdout in real-time
            print_stderr: If True, prints stderr in real-time
            watch_signals: Set of signals to watch for (e.g., {signal.SIGINT, signal.SIGTERM})
                          If any of these signals are received, the process will be terminated
        
        Returns:
            Tuple of (stdout_content, stderr_content, return_code)
        """

        self.logger.debug(f"DEBUG - Executing command: {command}")
        
        # Parse command if it's a string.  POSIX shlex treats Windows
        # backslashes as escape characters, turning e.g. ``C:\\data`` into
        # ``C:data``.  Use the Windows command-line parser on Windows so
        # generated DLIO paths survive intact.
        if isinstance(command, str):
            cmd_args = _split_command(command)
        else:
            cmd_args = command

        # ``select.select`` only accepts sockets on Windows.  The normal
        # implementation below uses select on subprocess pipes for live
        # output, so use reader threads for Windows pipes instead.
        if os.name == "nt":
            command_text = command if isinstance(command, str) else None
            if command_text is None and command and command[0].lower() in {"true", "false", "echo", "ls"}:
                command_text = subprocess.list2cmdline(command)
            return self._execute_windows(
                cmd_args,
                command_text=command_text,
                print_stdout=print_stdout,
                print_stderr=print_stderr,
                watch_signals=watch_signals,
            )
        
        # Set up signal handlers if requested
        if watch_signals:
            self._setup_signal_handlers(watch_signals)
        
        # Reset state
        self._stop_event.clear()
        self.terminated_by_signal = False
        self.signal_received = None
        
        # Initialize output buffers
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        return_code = None
        
        try:
            # Start the process
            self.process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )
            
            # Get file descriptors for select
            stdout_fd = self.process.stdout.fileno()
            stderr_fd = self.process.stderr.fileno()
            
            # Process output until completion or signal
            while self.process.poll() is None and not self._stop_event.is_set():
                # Wait for output with timeout to allow checking for signals
                readable, _, _ = select.select(
                    [self.process.stdout, self.process.stderr], 
                    [], 
                    [], 
                    0.1
                )
                
                for stream in readable:
                    # read1() returns whatever bytes are in the pipe buffer without
                    # blocking for '\n', preventing a hang on \r-terminated output.
                    raw = stream.buffer.read1(65536)
                    if not raw:  # EOF
                        continue
                    line = raw.decode('utf-8', errors='replace')
                        
                    if stream.fileno() == stdout_fd:
                        stdout_buffer.write(line)
                        if print_stdout:
                            sys.stdout.write(line)
                            sys.stdout.flush()
                    elif stream.fileno() == stderr_fd:
                        stderr_buffer.write(line)
                        if print_stderr:
                            sys.stderr.write(line)
                            sys.stderr.flush()
            
            # Drain any remaining output.  TextIOWrapper.read() blocks until
            # EOF, which never arrives if orphaned grandchild processes
            # (e.g. PyTorch DataLoader workers forked inside a DLIO MPI rank
            # *after* MPI_Init) still hold the pipe write-end open.
            # select() + read1() with a short timeout avoids that hang:
            # when the write-end is fully closed select() returns immediately
            # (EOF is readable), so the normal path has no added latency.
            for stream, buf, print_flag, sys_out in [
                (self.process.stdout, stdout_buffer, print_stdout, sys.stdout),
                (self.process.stderr, stderr_buffer, print_stderr, sys.stderr),
            ]:
                while True:
                    ready, _, _ = select.select([stream], [], [], 0.5)
                    if not ready:
                        break
                    chunk = stream.buffer.read1(65536)
                    if not chunk:
                        break
                    text = chunk.decode('utf-8', errors='replace')
                    buf.write(text)
                    if print_flag:
                        sys_out.write(text)
                        sys_out.flush()
            
            # Get the return code
            return_code = self.process.poll()
            
            # Check if we were terminated by a signal
            if self.terminated_by_signal:
                self.logger.debug(f"DEBUG - Process terminated by signal: {self.signal_received}")
                
            return stdout_buffer.getvalue(), stderr_buffer.getvalue(), return_code
            
        finally:
            # Clean up
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            
            # Restore original signal handlers
            self._restore_signal_handlers()

    def _execute_windows(
        self,
        cmd_args: List[str],
        command_text: Optional[str] = None,
        print_stdout: bool = False,
        print_stderr: bool = False,
        watch_signals: Optional[Set[int]] = None,
    ) -> Tuple[str, str, int]:
        """Execute a command while streaming Windows subprocess pipes.

        Windows does not support ``select()`` on anonymous pipes.  Dedicated
        reader threads preserve the live-output behaviour without relying on
        Unix file-descriptor semantics.
        """
        self._stop_event.clear()
        self.terminated_by_signal = False
        self.signal_received = None

        if watch_signals:
            self._setup_signal_handlers(watch_signals)

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        def _write_console(output_stream, text):
            """Write child-process output without letting console encoding stop the drain.

            Windows consoles are still commonly configured for a legacy code page
            (for example GBK).  Benchmark output can contain Unicode symbols, and
            an encoding error in a reader thread would close the pipe while the
            child is still writing.  Treat the live console as best-effort while
            always retaining the UTF-8 text in the returned buffers.
            """
            try:
                output_stream.write(text)
                output_stream.flush()
                return
            except (UnicodeEncodeError, UnicodeDecodeError, OSError, ValueError):
                pass

            try:
                encoding = getattr(output_stream, "encoding", None) or "utf-8"
                safe_text = text.encode(encoding, errors="replace").decode(
                    encoding, errors="replace"
                )
                output_stream.write(safe_text)
                output_stream.flush()
            except (UnicodeEncodeError, UnicodeDecodeError, OSError, ValueError):
                # Logging to the console must never make the benchmark fail.
                return

        def _drain(stream, buffer, print_flag, output_stream):
            try:
                for line in iter(stream.readline, ""):
                    buffer.write(line)
                    if print_flag:
                        _write_console(output_stream, line)
            finally:
                stream.close()

        # A few callers (and the long-standing unit tests) use POSIX shell
        # built-ins as tiny probes.  Keep those probes working on Windows;
        # normal benchmark commands continue through CreateProcess with an
        # argv list and no shell.
        popen_args = cmd_args
        use_shell = False
        if command_text and cmd_args:
            first = cmd_args[0].lower()
            if first in {"true", "false"}:
                popen_args = [
                    os.environ.get("COMSPEC", "cmd.exe"),
                    "/d",
                    "/c",
                    f"exit {'0' if first == 'true' else '1'}",
                ]
            elif first in {"echo", "ls"}:
                popen_args = command_text
                use_shell = True

        try:
            self.process = subprocess.Popen(
                popen_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=use_shell,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            stdout_thread = threading.Thread(
                target=_drain,
                args=(self.process.stdout, stdout_buffer, print_stdout, sys.stdout),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_drain,
                args=(self.process.stderr, stderr_buffer, print_stderr, sys.stderr),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()

            while self.process.poll() is None and not self._stop_event.is_set():
                self._stop_event.wait(0.1)

            if self._stop_event.is_set() and self.process.poll() is None:
                self.process.terminate()
            return_code = self.process.wait()
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
            return stdout_buffer.getvalue(), stderr_buffer.getvalue(), return_code
        finally:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self._restore_signal_handlers()
    
    def _setup_signal_handlers(self, signals: Set[int]):
        """Set up signal handlers for the specified signals."""
        self._original_handlers = {}
        
        def signal_handler(sig, frame):
            self.logger.debug(f"DEBUG - Received signal: {sig}")
            self.terminated_by_signal = True
            self.signal_received = sig
            self._stop_event.set()
            
            if self.process and self.process.poll() is None:
                self.process.terminate()

            for handler in self._original_handlers.values():
                handler(sig, frame)
        
        for sig in signals:
            self._original_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, signal_handler)
    
    def _restore_signal_handlers(self):
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)
        self._original_handlers = {}


def _mpi_params_contain_flag(params: Optional[List[str]], flag: str) -> bool:
    """Return True if ``params`` already specifies the MPI ``flag``.

    Matches any of the surface forms a user may pass through ``--mpi-params``:
    ``--flag``, ``-flag``, ``--flag=value``, ``-flag=value``. ``flag`` is the
    bare name without leading dashes (e.g. ``"bind-to"``).
    """
    if not params:
        return False
    candidates = {f"--{flag}", f"-{flag}"}
    for tok in params:
        if not isinstance(tok, str):
            continue
        head = tok.split("=", 1)[0]
        if head in candidates:
            return True
    return False


def generate_mpi_prefix_cmd(
    mpi_cmd: str,
    hosts: List[str],
    num_processes: int,
    oversubscribe: bool,
    allow_run_as_root: bool,
    params: Optional[List[str]],
    logger: logging.Logger,
    mpi_btl: str = "auto",
    processes_per_node: Optional[int] = None,
) -> str:
    """Generate MPI command prefix for distributed execution.

    Constructs the mpirun/mpiexec command prefix with proper host
    distribution, slot allocation, and CPU binding settings.

    Args:
        mpi_cmd: MPI binary to use ('mpirun' or 'mpiexec').
        hosts: List of hostnames, optionally with slots (e.g., 'host1:4').
        num_processes: Total number of MPI processes to run.
        oversubscribe: Allow more processes than available CPU slots.
        allow_run_as_root: Allow running MPI as root user.
        params: Additional MPI parameters to append.
        logger: Logger instance for debug output.
        mpi_btl: Byte Transport Layer for single-host runs. 'auto' lets
            OpenMPI select automatically (default). 'vader' forces POSIX
            shared-memory transport. 'tcp' forces TCP loopback (most
            compatible; recommended for containers/root). Ignored for
            multi-host runs.
        processes_per_node: Number of MPI processes per node. When not None,
            injects ``--npernode N`` into the prefix after the host list and
            before bind/map directives. Default None (no injection).

    Returns:
        MPI command prefix string ready for command execution.

    Raises:
        ValueError: If configured slots are insufficient for num_processes.
        ValueError: If unsupported MPI command is specified.

    Example:
        >>> prefix = generate_mpi_prefix_cmd(
        ...     'mpirun', ['host1', 'host2'], 8, False, False, None, logger,
        ...     processes_per_node=4
        ... )
        >>> prefix
        'mpirun -n 8 -host host1:4,host2:4 --npernode 4 --bind-to none --map-by node'
    """
    # Check if we got slot definitions with the hosts
    slots_configured = any(":" in host for host in hosts)

    if slots_configured:
        # Ensure the configured number of slots is >= num_processes
        num_slots = sum(int(slot) for _, slot in (host.split(":") for host in hosts))
        logger.debug(f"Configured slots: {num_slots}")
        if num_slots < num_processes:
            raise ValueError(
                f"Configured slots ({num_slots}) are not sufficient "
                f"to run {num_processes} processes"
            )
    else:
        # Manually define slots to evenly distribute processes across hosts
        slotted_hosts: List[str] = []
        base_slots_per_host = num_processes // len(hosts)
        remaining_slots = num_processes % len(hosts)

        for i, host in enumerate(hosts):
            slots_for_this_host = base_slots_per_host + (1 if i < remaining_slots else 0)
            slotted_hosts.append(f"{host}:{slots_for_this_host}")

        hosts = slotted_hosts
        logger.debug(f"Configured slots for hosts: {hosts}")

    # Build MPI command prefix
    # ---- HPE Cray PALS mpiexec (ALCF Crux/Polaris/Aurora) ----
    # PALS mpiexec uses `--ppn` and a bare comma-separated `--hosts` list, with
    # `--cpu-bind` for affinity. It does NOT accept the OpenMPI flags this
    # function emits for mpirun (`-host h:slots`, `--npernode`, `--bind-to`,
    # `--map-by`, `--mca`, `--oversubscribe`, `--allow-run-as-root`), so build a
    # PALS-native prefix and return early. Without this, `--mpi-bin mpiexec`
    # produces an argv PALS cannot parse and every ALCF run fails to launch.
    if mpi_cmd == MPIEXEC:
        pals_hosts: List[str] = []
        for host in hosts:
            host_part = host.split(':')[0]
            if host_part not in pals_hosts:
                pals_hosts.append(host_part)
        ranks_per_node = processes_per_node
        if ranks_per_node is None:
            # Ceil-divide so every node has enough slots for num_processes.
            ranks_per_node = -(-num_processes // len(pals_hosts))
        prefix = (
            f"{MPI_EXEC_BIN} -n {num_processes}"
            f" --ppn {ranks_per_node}"
            f" --hosts {','.join(pals_hosts)}"
        )
        # PALS affinity flag is --cpu-bind (not OpenMPI's --bind-to/--map-by).
        if not _mpi_params_contain_flag(params, "cpu-bind"):
            prefix += " --cpu-bind none"
        if params:
            for param in params:
                prefix += f" {param}"
        return prefix

    # ---- OpenMPI mpirun ----
    if mpi_cmd == MPIRUN:
        prefix = f"{MPI_RUN_BIN} -n {num_processes} -host {','.join(hosts)}"
    else:
        raise ValueError(f"Unsupported MPI command: {mpi_cmd}")

    if processes_per_node is not None:
        prefix += f" --npernode {processes_per_node}"

    # CPU scheduling optimizations for I/O workloads
    unique_hosts: Set[str] = set()
    for host in hosts:
        host_part = host.split(':')[0] if ':' in host else host
        unique_hosts.add(host_part)

    is_multi_host = len(unique_hosts) > 1

    # OpenMPI rejects duplicate --bind-to / --map-by occurrences, so suppress
    # the default for whichever of those flags the user supplied via --mpi-params.
    user_set_bind_to = _mpi_params_contain_flag(params, "bind-to")
    user_set_map_by = _mpi_params_contain_flag(params, "map-by")

    if not user_set_bind_to:
        prefix += " --bind-to none"
    if not user_set_map_by:
        prefix += " --map-by node" if is_multi_host else " --map-by socket"

    if is_multi_host:
        logger.info("MPI BTL transport: auto (multi-host run; transport managed by network fabric)")
    else:
        # Single-host: optimize for NUMA domains
        if mpi_btl == "vader":
            prefix += " --mca btl vader,self"
            logger.info("MPI BTL transport: vader (POSIX shared-memory)")
        elif mpi_btl == "tcp":
            prefix += " --mca btl tcp,self"
            logger.info("MPI BTL transport: tcp (TCP loopback; recommended for containers/root)")
        else:  # auto
            logger.info("MPI BTL transport: auto (OpenMPI default selection)")

    if oversubscribe:
        prefix += " --oversubscribe"

    if allow_run_as_root:
        prefix += " --allow-run-as-root"

    if params:
        for param in params:
            prefix += f" {param}"

    return prefix

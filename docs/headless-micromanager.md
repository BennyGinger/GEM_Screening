# Headless Micro-Manager

Open GEM Screening, configure the experiment, select the lamp in Microscope
settings, and click Run (or Rescue). The worker starts the Java headless backend
and loads the hardware configuration before the workflow creates A1Manager.
Micro-Manager does not need to be opened manually. Close its desktop application
before starting a run so it does not occupy the bridge port or hardware.

The installation path and lamp-to-config mapping live in
`gem_screening/runtime/micromanager.py`:

The backend runs from `C:\Program Files\Micro-Manager-2.0`, as required by the
microscope's device drivers. Hardware configurations remain in that installation's
`config_files` folder. The backend installation and config directory are separate
constants. This installation contains `PycroManagerJava-0.25.0.jar`. GEM starts
that legacy launcher directly with its four required JARs rather than scanning
the full plugins directory. It waits for `Headless mode started`, connects through
Pycro-Manager, enables Core logging, and explicitly loads the selected `.cfg`.
No Java libraries or device drivers in the installation are replaced.

| Selected lamp | Configuration under `C:\Program Files\Micro-Manager-2.0\config_files` |
| --- | --- |
| pE-800 | `v1_Andor_p800.cfg` |
| pE-4000 | `v1_Andor_p4000.cfg` |

These configurations intentionally do not load Mosaic or MarZ. DMD stimulation
and injection require different configurations and are outside this initial
headless setup. DiaLamp-only startup is not supported. OughtaFocus is rejected;
use Manual or sq_grad autofocus.

Each GUI run owns one backend. It closes the active shutter, unloads devices,
releases the Java client proxies, and stops the backend when the workflow completes, fails or reaches a cancellation
checkpoint. Subsequent runs start fresh with the current lamp selection. Startup
has a 60-second watchdog and reports progress every five seconds at DEBUG level.
The configured timeout is also logged at DEBUG; actual timeout failures remain errors. If Java never
reports readiness, the watchdog stops the backend to release the blocked launcher
and reports a startup failure in the console. The timeout constant lives in the
runtime module. Device calls are blocking inside the worker; cancellation takes
effect after startup returns or times out. Existing command-line workflow callers retain their current
connection behavior.

The GUI console reports startup errors. Java stdout/stderr is captured from the
start in `logs/micromanager-startup.log`, including failures before Core logging
is available. Micro-Manager's Core log is written to `logs/micromanager.log`
before loading devices. Both files live inside the experiment folder. Keep the existing vendor
drivers and Micro-Manager installation (including its bundled Java runtime).

To check on the microscope PC: select the appropriate lamp, run a small imaging
experiment, confirm the selected config in the console and verify a camera image.
Then check that the backend stops and a second run can start. Hardware startup
loads and initializes real devices; normal workflow initialization also moves
the stage to its existing predefined position.

VASTcode21 v1.2.2 MT5 Strategy Tester launch hotfix

Problem fixed
-------------
MetaTrader5.initialize() was used for automatic broker-symbol discovery before
real-tick validation. On this Windows/MT5 installation, mt5.shutdown() detached
the Python API but could leave terminal64.exe running. The next command-line
launch with /config:<tester.ini> then attached to that already-running terminal,
so MT5 opened normally instead of starting automatic Strategy Tester mode. The
bridge saw exit code 0 but no HTML report was produced.

What v1.2.2 changes
-------------------
* Snapshots terminal64.exe PIDs before symbol discovery.
* If a user MT5 terminal already exists, validation is still safely deferred.
* Captures MT5 data_path during symbol discovery and exports MT5_DATA_PATH so
  MT5Tester does not initialize MT5 again just to discover the data directory.
* After symbol discovery, closes only terminal process(es) that appeared after
  the bridge's own snapshot. Pre-existing user MT5 processes are never touched.
* Tries normal task termination first; force termination is limited to those
  exact bridge-spawned PIDs if they remain after a grace period.
* If a bridge-spawned terminal still cannot be closed, validation stops before
  Strategy Tester launch rather than risking a wrong/interactive session.

Safety policy unchanged
-----------------------
* Live trading remains OFF for generated validation EAs.
* Paid services remain OFF.
* GOLD and BITCOIN scope unchanged.
* No broker credentials or VC21_CORE_KEY are added to the repository.
* The bridge never closes an MT5 terminal that was already running before its
  own symbol-discovery operation.

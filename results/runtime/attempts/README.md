# Earlier runtime attempts

These attempts are separate from the latest root-level status and summary.

- `20261003T093946719584Z`: diagnostic run on `dbaas-smoke-44f9ccbea2`. API provisioning passed; the backup TCP source fix was applied to the existing disposable release before rerunning lifecycle checks. PITR and primary/replica failure checks passed. PgCat used a **rolling restart**, not the later force-delete profile. This is not a clean final run.
- `20261003T095314656680Z`: clean run on `dbaas-smoke-c96bfafa8e`. Provisioning, SQL, backup and WAL passed; PITR failed during Helm uninstall because Patroni recreated its configuration Service. PVC deletion was not reached. The source fix stops Patroni before removing its Services.
- `20261003T100030579634Z`: clean run on `dbaas-smoke-68bac400b4`. PITR passed after the shutdown fix. Primary failure did not produce a different primary within 180 seconds: the original primary was recreated and regained leadership. The promotion assertion correctly failed. The final profile holds replacement scheduling to exercise actual replica promotion. Final failure artifacts were moved into this attempt after its process exited.

Earlier bootstrap investigations are summarized in the report and shared sanitized connectivity logs. No success here overrides a failed or unexecuted check in the latest summary.

# Partial rehearsal

Both database alerts completed all transitions. BackupJobFailed reached firing, but log collection failed after the failed Job controller removed its OnFailure pod. The Job object proves BackoffLimitExceeded. The Job was deleted in finally. The next backup-only attempt uses restartPolicy Never and backoffLimit 0 to preserve the failure pod for logs; the backup script and missing-primary selector are unchanged.

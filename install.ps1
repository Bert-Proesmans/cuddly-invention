Function Ensure-ExecutableExists {
    Param
    (
        [Parameter( Mandatory = $True )]
        [string]
        $Executable,

        [string]
        $MinimumVersion = ""
    )

    $CurrentVersion = ( Get-Command -Name $Executable -ErrorAction Stop ).Version

    If ( $MinimumVersion ) {
        $RequiredVersion = [version]$MinimumVersion

        If ( $CurrentVersion -lt $RequiredVersion ) {
            Throw "$( $Executable ) version $( $CurrentVersion ) does not meet requirements [> $( $MinimumVersion )"
        }
    }
}

# MAIN
Ensure-ExecutableExists -Executable "py" -MinimumVersion "3.6" -ErrorAction Stop

$action = New-ScheduledTaskAction -Execute 'py.exe' -Argument "-3 `"$PSScriptRoot/payment.py`""
$trigger = New-ScheduledTaskTrigger -Daily -At "20:00"
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "TeamLeader payment processor" `
        -Description "Daily processing of upload timesheets through TeamLeader."
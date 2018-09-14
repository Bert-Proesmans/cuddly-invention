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

function EnsurePython3() {
    try {
        Ensure-ExecutableExists -Executable "py" -MinimumVersion "3.6"
        # Print python details
        & {py.exe -3 -V}
    } catch {
        Write-Host "Downloading Python 3.6.6"
        $url = "https://www.python.org/ftp/python/3.6.6/python-3.6.6.exe"
        $outpath = "$PSScriptRoot/python-3.6.6.exe"
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $outpath)

        Write-Host "Installing Python 3.6.6"
        # TODO(Bert): Find out how to silently install
        $args = @("")
        Start-Process -Filepath "$PSScriptRoot/python-3.6.6.exe" -ArgumentList $args
    }
}

function EnsurePip3() {
    $exec = & {py.exe -3 -m pip} | Out-String
    if ($LASTEXITCODE -gt 0) {
        Write-Host "Installing PIP"
        try {
            $localFileName = "$( $PSScriptRoot )\get-pip.py"
            (New-Object System.Net.WebClient).DownloadFile('https://bootstrap.pypa.io/get-pip.py', $localFileName)
            $exec = & {py.exe -3 $localFileName} 2>&1 | Out-String
            if ($LASTEXITCODE -gt 0) {
                throw "Error running PIP install!"
            }
            Write-Host $exec
        }
        catch {
            $msg = $_.Exception.Message
            Write-Error "Error installing PIP: $( $msg ), exiting..."
            Exit 2
        }
        finally {
            If (Test-Path $localFileName) {
                Remove-Item $localFileName
            }
        }
    }
    else {
        Write-Host "Python PIP found"
    }
}

function EnsureEnvironment() {
    Write-Host "Installing python packages"

    $exec = & {py.exe -3 -m pip install requests} 2>&1 | Out-String
    if ($LASTEXITCODE -gt 0) {
        Write-Host $exec    
        Write-Error "Error installing python packages!"
        Exit 3
    } 
}

# MAIN
EnsurePython3
EnsurePip3
EnsureEnvironment
Write-Host "==OK=="
Exit 0
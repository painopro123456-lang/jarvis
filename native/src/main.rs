use serde_json::{json, Value};
use std::process::{Command, Stdio};

fn powershell(script: &str) -> Result<String, String> {
    #[cfg(not(target_os = "windows"))]
    { let _ = script; return Err("The JARVIS native system core currently targets Windows.".into()); }
    #[cfg(target_os = "windows")]
    {
        let output = Command::new("powershell.exe")
            .args(["-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script])
            .stdin(Stdio::null())
            .output()
            .map_err(|e| format!("Could not start Windows PowerShell: {e}"))?;
        if !output.status.success() {
            return Err(String::from_utf8_lossy(&output.stderr).trim().to_string());
        }
        let text = String::from_utf8_lossy(&output.stdout).trim_start_matches('\u{feff}').trim().to_string();
        if text.is_empty() { return Err("Windows returned no diagnostic data.".into()); }
        Ok(text)
    }
}

fn driver_audit() -> Result<Value, String> {
    // Read-only: queries Plug-and-Play driver inventory and Windows Update's
    // driver category. It never downloads or installs a driver.
    let script = r#"
$ErrorActionPreference = 'Stop'
$devices = @(Get-CimInstance -ClassName Win32_PnPSignedDriver |
  Where-Object { $_.DeviceName -and $_.DriverVersion } |
  Select-Object DeviceName, Manufacturer, DriverVersion, DriverDate, InfName, IsSigned)
$updates = @()
$scanError = $null
try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $result = $searcher.Search("IsInstalled=0 and Type='Driver' and IsHidden=0")
  foreach ($update in $result.Updates) {
    $updates += [pscustomobject]@{
      Title = $update.Title
      Description = $update.Description
      IsDownloaded = $update.IsDownloaded
      EulaAccepted = $update.EulaAccepted
    }
  }
} catch { $scanError = $_.Exception.Message }
[pscustomobject]@{
  scanned_at = (Get-Date).ToString('o')
  installed_drivers = $devices
  available_driver_updates = $updates
  update_scan_error = $scanError
} | ConvertTo-Json -Depth 5 -Compress
"#;
    let raw = powershell(script)?;
    serde_json::from_str(&raw).map_err(|e| format!("Could not parse Windows driver report: {e}. Output: {}", raw.chars().take(500).collect::<String>()))
}

fn main() {
    let command = std::env::args().nth(1).unwrap_or_default();
    let result = match command.as_str() {
        "drivers" => driver_audit(),
        "health" => Ok(json!({
            "engine": "JARVIS Rust Core",
            "version": env!("CARGO_PKG_VERSION"),
            "platform": std::env::consts::OS,
            "capabilities": ["read-only-driver-inventory", "windows-update-driver-discovery"]
        })),
        _ => Err("Unknown command. Supported commands: health, drivers".into()),
    };
    match result {
        Ok(value) => println!("{}", value),
        Err(error) => {
            eprintln!("{error}");
            std::process::exit(2);
        }
    }
}

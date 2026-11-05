"""Generate a PnP.PowerShell provisioning script that recreates the pack in a Microsoft 365 tenant."""
import re
from pathlib import Path

from .common import slugify


def _ps(s):
    return "'" + str(s).replace("'", "''") + "'"


def internal_name(col):
    parts = re.split(r"[^A-Za-z0-9]+", col)
    n = "".join(p[:1].upper() + p[1:] for p in parts if p)
    if not n or not n[0].isalpha():
        n = "F" + n
    return n[:32]


def write_pnp(sites, lists, out_dir, company, prefix):
    """sites: [{key, title, alias, folder, description, libraries:[{title, url}] , hub:bool}]
    lists: [{site_alias, title, url, csv, columns:[(name, internal, type)], rows}]"""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    site_ps = []
    for s in sites:
        libs = ", ".join("@{Title=%s; Url=%s}" % (_ps(l["title"]), _ps(l["url"])) for l in s["libraries"])
        site_ps.append("    @{Key=%s; Title=%s; Alias=%s; Folder=%s; Description=%s; IsHub=$%s; Libraries=@(%s)}" % (
            _ps(s["key"]), _ps(s["title"]), _ps(s["alias"]), _ps(s["folder"]), _ps(s.get("description", "")[:240]),
            "true" if s.get("hub") else "false", libs))
    list_ps = []
    for l in lists:
        cols = ", ".join("@{Name=%s; Internal=%s; Type=%s}" % (_ps(c[0]), _ps(c[1]), _ps(c[2])) for c in l["columns"])
        list_ps.append("    @{Site=%s; Title=%s; Url=%s; Csv=%s; Columns=@(%s)}" % (
            _ps(l["site_alias"]), _ps(l["title"]), _ps(l["url"]), _ps(l["csv"]), cols))

    script = f"""<#
.SYNOPSIS
  Provisions the {company['fictional_name']} fictional training tenant content into SharePoint Online.

.DESCRIPTION
  Creates one communication site per department (plus the intranet hub), registers the hub,
  creates document libraries, uploads every file from the SharePoint folder of this pack
  (preserving folders), and creates SharePoint lists from the CSV datasets.

  Re-runnable: existing sites, libraries, lists and files are reused/overwritten.
  ALL CONTENT IS FICTIONAL TRAINING DATA.

.REQUIREMENTS
  * PowerShell 7.4+  and  Install-Module PnP.PowerShell -Scope CurrentUser
  * An Entra ID app registration for PnP interactive login (one-off, see README.md):
      Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP Training Provisioning" -Tenant <tenant>.onmicrosoft.com
  * SharePoint Administrator rights (to create sites).

.EXAMPLE
  ./Provision-SharePoint.ps1 -TenantName contoso -ClientId 00000000-0000-0000-0000-000000000000

.EXAMPLE
  # Several fictional companies in one tenant: give each its own learner group
  ./Provision-SharePoint.ps1 -TenantName contoso -ClientId <id> -LearnerGroup "{company['fictional_name']} Learners"
#>
param(
    [Parameter(Mandatory)] [string]$TenantName,
    [Parameter(Mandatory)] [string]$ClientId,
    [string]$SitePrefix = {_ps(prefix)},
    [string]$OwnerEmail,
    [int]$MaxListRows = 300,
    [switch]$SkipFiles,
    [switch]$SkipLists,
    [string[]]$OnlySites,
    # Entra security group (display name or object id) granted access to every site; created if missing
    [string]$LearnerGroup,
    [ValidateSet('Read', 'Edit')] [string]$LearnerRole = 'Read'
)
$ErrorActionPreference = 'Stop'
$PackRoot  = Split-Path -Parent $PSScriptRoot
$SpRoot    = Join-Path $PackRoot 'SharePoint'
$DataRoot  = Join-Path $PackRoot 'Databases' 'csv'
$BaseUrl   = "https://$TenantName.sharepoint.com"
$AdminUrl  = "https://$TenantName-admin.sharepoint.com"

$Sites = @(
{chr(10).join(site_ps)}
)

$Lists = @(
{chr(10).join(list_ps)}
)

function Site-Url($alias) {{ "$BaseUrl/sites/$SitePrefix-$alias" }}

Write-Host "Connecting to SharePoint admin ($AdminUrl)..." -ForegroundColor Cyan
Connect-PnPOnline -Url $AdminUrl -Interactive -ClientId $ClientId
if (-not $OwnerEmail) {{ $OwnerEmail = (Get-PnPProperty -ClientObject (Get-PnPWeb) -Property CurrentUser).Email }}

# ---- 1. Sites ---------------------------------------------------------------------------
foreach ($s in $Sites) {{
    if ($OnlySites -and $s.Key -notin $OnlySites) {{ continue }}
    $url = Site-Url $s.Alias
    $existing = Get-PnPTenantSite -Identity $url -ErrorAction SilentlyContinue
    if (-not $existing) {{
        Write-Host "Creating site $($s.Title) -> $url" -ForegroundColor Green
        New-PnPSite -Type CommunicationSite -Title $s.Title -Url $url -Description $s.Description -Owner $OwnerEmail -Wait | Out-Null
    }} else {{ Write-Host "Site exists: $url" }}
}}

# ---- 2. Hub -----------------------------------------------------------------------------
$hub = $Sites | Where-Object {{ $_.IsHub }} | Select-Object -First 1
if ($hub) {{
    $hubUrl = Site-Url $hub.Alias
    try {{ Register-PnPHubSite -Site $hubUrl -ErrorAction Stop | Out-Null; Write-Host "Registered hub $hubUrl" }}
    catch {{ Write-Host "Hub already registered (or no permission): $($_.Exception.Message)" -ForegroundColor Yellow }}
    foreach ($s in $Sites | Where-Object {{ -not $_.IsHub }}) {{
        if ($OnlySites -and $s.Key -notin $OnlySites) {{ continue }}
        try {{ Add-PnPHubSiteAssociation -Site (Site-Url $s.Alias) -HubSite $hubUrl -ErrorAction Stop }} catch {{ }}
    }}
}}

# ---- 3. Libraries + files ---------------------------------------------------------------
foreach ($s in $Sites) {{
    if ($OnlySites -and $s.Key -notin $OnlySites) {{ continue }}
    $url = Site-Url $s.Alias
    Connect-PnPOnline -Url $url -Interactive -ClientId $ClientId
    foreach ($lib in $s.Libraries) {{
        if (-not (Get-PnPList -Identity $lib.Url -ErrorAction SilentlyContinue)) {{
            New-PnPList -Title $lib.Title -Url $lib.Url -Template DocumentLibrary -OnQuickLaunch | Out-Null
            Write-Host "  + library $($lib.Title)"
        }}
        if ($SkipFiles) {{ continue }}
        $local = Join-Path $SpRoot $s.Folder $lib.Title
        if (-not (Test-Path $local)) {{ continue }}
        Get-ChildItem $local -File -Recurse | ForEach-Object {{
            $rel = [IO.Path]::GetRelativePath($local, $_.DirectoryName) -replace '\\\\','/'
            $dest = if ($rel -eq '.') {{ $lib.Url }} else {{ "$($lib.Url)/$rel" }}
            try {{
                Add-PnPFile -Path $_.FullName -Folder $dest -Values @{{ Modified = $_.LastWriteTime }} | Out-Null
            }} catch {{
                Add-PnPFile -Path $_.FullName -Folder $dest | Out-Null
            }}
            Write-Host "    ^ $dest/$($_.Name)"
        }}
    }}
}}

# ---- 4. Lists from CSV ------------------------------------------------------------------
if (-not $SkipLists) {{
    foreach ($l in $Lists) {{
        $site = $Sites | Where-Object {{ $_.Alias -eq $l.Site }}
        if ($OnlySites -and $site.Key -notin $OnlySites) {{ continue }}
        Connect-PnPOnline -Url (Site-Url $l.Site) -Interactive -ClientId $ClientId
        if (-not (Get-PnPList -Identity $l.Url -ErrorAction SilentlyContinue)) {{
            New-PnPList -Title $l.Title -Url $l.Url -Template GenericList -OnQuickLaunch | Out-Null
            foreach ($c in $l.Columns | Select-Object -Skip 1) {{
                Add-PnPField -List $l.Url -DisplayName $c.Name -InternalName $c.Internal -Type $c.Type -AddToDefaultView | Out-Null
            }}
            Set-PnPField -List $l.Url -Identity 'Title' -Values @{{ Title = $l.Columns[0].Name }} | Out-Null
            Write-Host "  + list $($l.Title)"
        }} else {{ Write-Host "  list exists, appending rows: $($l.Title)" -ForegroundColor Yellow }}
        $rows = Import-Csv (Join-Path $DataRoot $l.Csv) | Select-Object -First $MaxListRows
        $batch = New-PnPBatch
        foreach ($r in $rows) {{
            $vals = @{{ Title = [string]$r.($l.Columns[0].Name) }}
            foreach ($c in $l.Columns | Select-Object -Skip 1) {{
                $v = $r.($c.Name)
                if ([string]::IsNullOrWhiteSpace($v)) {{ continue }}
                if ($c.Type -eq 'Boolean') {{ $v = @('1','true','True','Yes') -contains $v }}
                $vals[$c.Internal] = $v
            }}
            Add-PnPListItem -List $l.Url -Values $vals -Batch $batch | Out-Null
        }}
        Invoke-PnPBatch -Batch $batch
        Write-Host "    $($rows.Count) rows -> $($l.Title)"
    }}
}}

# ---- 5. Learner access -------------------------------------------------------------------
if ($LearnerGroup) {{
    Connect-PnPOnline -Url $AdminUrl -Interactive -ClientId $ClientId
    $grp = Get-PnPEntraIDGroup -Identity $LearnerGroup -ErrorAction SilentlyContinue
    if (-not $grp) {{
        Write-Host "Creating security group '$LearnerGroup'" -ForegroundColor Green
        $nick = ($LearnerGroup -replace '[^A-Za-z0-9]', '').ToLower()
        $grp = New-PnPEntraIDGroup -DisplayName $LearnerGroup -MailNickname $nick -IsSecurityEnabled `
            -Description "Learners for the {company['fictional_name']} fictional training company"
    }}
    $login = "c:0t.c|tenant|$($grp.Id)"
    foreach ($s in $Sites) {{
        if ($OnlySites -and $s.Key -notin $OnlySites) {{ continue }}
        Connect-PnPOnline -Url (Site-Url $s.Alias) -Interactive -ClientId $ClientId
        $spGroup = if ($LearnerRole -eq 'Edit') {{ Get-PnPGroup -AssociatedMemberGroup }} else {{ Get-PnPGroup -AssociatedVisitorGroup }}
        try {{ Add-PnPGroupMember -Group $spGroup -LoginName $login -ErrorAction Stop; Write-Host "  $LearnerGroup -> $($spGroup.Title)" }}
        catch {{ Write-Host "  could not add group to $($s.Title): $($_.Exception.Message)" -ForegroundColor Yellow }}
    }}
}}

Write-Host "`nDone. Hub: $(Site-Url ($hub.Alias))" -ForegroundColor Cyan
Write-Host "Note: Microsoft 365 Copilot / search can take several hours to index new content." -ForegroundColor Yellow
"""
    p = out / "Provision-SharePoint.ps1"
    p.write_text(script, encoding="utf-8-sig")
    (out / "Remove-Company.ps1").write_text(_remove_script(sites, company, prefix), encoding="utf-8-sig")

    readme = f"""# Provisioning {company['fictional_name']} into Microsoft 365

All content in this pack is **fictional** and intended for training use only. Use a training/dev tenant
(e.g. a Microsoft 365 Developer Program tenant), never a production tenant.

## One-off setup

```powershell
# PowerShell 7.4+
Install-Module PnP.PowerShell -Scope CurrentUser
# Create the Entra ID app PnP uses for interactive sign-in (needs admin consent):
Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP Training Provisioning" -Tenant <tenant>.onmicrosoft.com
# Note the Client ID it prints.
```

## Run

```powershell
cd "M365 Provisioning"
./Provision-SharePoint.ps1 -TenantName <tenant> -ClientId <client-id>
# Options:
#   -SitePrefix XYZ        prefix for site URLs (default {prefix}) - use per cohort to avoid clashes
#   -OnlySites hr,finance  provision only some department sites
#   -SkipFiles / -SkipLists
#   -MaxListRows 300       cap rows written to each SharePoint list
#   -LearnerGroup "<name>" Entra security group granted access to every site (created if missing)
#   -LearnerRole Read|Edit site visitors (default) or members
```

## Several fictional companies in one tenant
One tenant can hold many packs: each company's sites use their own prefix (`/sites/{prefix}-...`) and their own hub.
To keep each cohort on one company, give it a learner group:

```powershell
./Provision-SharePoint.ps1 -TenantName <tenant> -ClientId <client-id> -LearnerGroup "{company['fictional_name']} Learners"
```

Then add the cohort's learner accounts to that group (Entra admin centre). Creating the group needs the Graph
permission `Group.ReadWrite.All` on the PnP app; without it, create the security group by hand and pass its name.
Copilot only returns content the signed-in user can open, so learners only see their own company. Copilot Studio
agents can also be limited to a single site or library as knowledge. To run two cohorts on the same company, provision
it twice with different `-SitePrefix` values.

## Removing a company

```powershell
./Remove-Company.ps1 -TenantName <tenant> -ClientId <client-id>          # sites go to the recycle bin (93 days)
./Remove-Company.ps1 -TenantName <tenant> -ClientId <client-id> -Purge -RemoveGroup "{company['fictional_name']} Learners"
```

This deletes only this pack's sites (matched by prefix). It asks you to type the prefix to confirm; `-Force` skips that.

## What gets created

| Site | URL | Libraries |
|---|---|---|
""" + "\n".join(f"| {s['title']}{' (hub)' if s.get('hub') else ''} | /sites/{prefix}-{s['alias']} | {', '.join(l['title'] for l in s['libraries'])} |" for s in sites) + """

SharePoint lists: """ + (", ".join(f"{l['title']} ({l['site_alias']})" for l in lists) or "none") + """

## Not provisioned automatically
* **Emails** (`Communications/Email/*.eml`) - drag into an Outlook folder of a training mailbox. Every thread is
  also uploaded as a Word copy to a *Communications Archive* library, so Copilot can find it through SharePoint.
* **Teams chats** (`Communications/Teams`) - Teams history cannot be imported. Each chat is also uploaded as a Word
  transcript to a Communications Archive library.
* **Databases** (`Databases/`) - the SQLite DB/CSVs/Excel workbook are for Power BI, Dataverse imports,
  Copilot Studio knowledge, or Excel Copilot exercises.

## Copilot indexing
New SharePoint content can take a few hours (occasionally up to 24h) before Microsoft 365 Copilot can use it.
Learners need access to each site: use `-LearnerGroup`, or add them as site visitors yourself.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    return p


def _remove_script(sites, company, prefix):
    site_ps = "\n".join("    @{Title=%s; Alias=%s; IsHub=$%s}" % (_ps(s["title"]), _ps(s["alias"]), "true" if s.get("hub") else "false")
                        for s in sites)
    return f"""<#
.SYNOPSIS
  Removes the {company['fictional_name']} fictional training sites from a SharePoint tenant.

.DESCRIPTION
  Deletes only the sites this pack created (/sites/<SitePrefix>-<alias>), so other fictional companies in the
  same tenant are untouched. Deleted sites go to the tenant recycle bin (restorable for 93 days) unless -Purge.

.EXAMPLE
  ./Remove-Company.ps1 -TenantName contoso -ClientId <id>
  ./Remove-Company.ps1 -TenantName contoso -ClientId <id> -Purge -RemoveGroup "{company['fictional_name']} Learners"
#>
param(
    [Parameter(Mandatory)] [string]$TenantName,
    [Parameter(Mandatory)] [string]$ClientId,
    [string]$SitePrefix = {_ps(prefix)},
    [switch]$Purge,
    [string]$RemoveGroup,
    [switch]$Force
)
$ErrorActionPreference = 'Stop'
$BaseUrl  = "https://$TenantName.sharepoint.com"
$AdminUrl = "https://$TenantName-admin.sharepoint.com"

$Sites = @(
{site_ps}
)

function Site-Url($alias) {{ "$BaseUrl/sites/$SitePrefix-$alias" }}

Write-Host "This will delete:" -ForegroundColor Yellow
$Sites | ForEach-Object {{ Write-Host "  $(Site-Url $_.Alias)" }}
if (-not $Force) {{
    $answer = Read-Host "Type the prefix '$SitePrefix' to confirm"
    if ($answer -ne $SitePrefix) {{ Write-Host "Cancelled."; return }}
}}

Connect-PnPOnline -Url $AdminUrl -Interactive -ClientId $ClientId
$hub = $Sites | Where-Object {{ $_.IsHub }} | Select-Object -First 1
if ($hub) {{
    try {{ Unregister-PnPHubSite -Site (Site-Url $hub.Alias) -ErrorAction Stop; Write-Host "Unregistered hub" }}
    catch {{ Write-Host "Hub not registered: $($_.Exception.Message)" }}
}}
foreach ($s in $Sites) {{
    $url = Site-Url $s.Alias
    if (-not (Get-PnPTenantSite -Identity $url -ErrorAction SilentlyContinue)) {{ Write-Host "Not found: $url"; continue }}
    Remove-PnPTenantSite -Url $url -Force
    Write-Host "Deleted $url" -ForegroundColor Green
    if ($Purge) {{
        # the deleted site can take a moment to reach the recycle bin
        for ($i = 0; $i -lt 12; $i++) {{
            try {{ Remove-PnPTenantDeletedSite -Identity $url -Force -ErrorAction Stop; Write-Host "  purged"; break }}
            catch {{ Start-Sleep -Seconds 10 }}
        }}
    }}
}}
if ($RemoveGroup) {{
    try {{ Remove-PnPEntraIDGroup -Identity $RemoveGroup -ErrorAction Stop; Write-Host "Removed group $RemoveGroup" }}
    catch {{ Write-Host "Could not remove group: $($_.Exception.Message)" -ForegroundColor Yellow }}
}}
Write-Host "Done." -ForegroundColor Cyan
"""


def list_columns(meta):
    cols = []
    for c in meta["columns"]:
        t = meta["types"].get(c, "TEXT")
        ptype = "Number" if t in ("INTEGER", "REAL") else "Text"
        if t == "TEXT" and any(k in c.lower() for k in ("date", "_on", "_at")):
            ptype = "DateTime"
        if t == "TEXT" and any(k in c.lower() for k in ("notes", "description", "comment", "summary")):
            ptype = "Note"
        cols.append((c, internal_name(c), ptype))
    return cols


def lib_url(title):
    return re.sub(r"[^A-Za-z0-9]", "", title.title())[:50] or "Documents"

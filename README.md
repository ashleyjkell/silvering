# Silvering Homes training pack

Silvering Homes is a **fictional** housing association in mid Kent, built as a practice environment for Microsoft 365 Copilot training. Every person, scheme, supplier and figure is invented.

**Live site:** https://ashleyjkell.github.io/silvering/. It's a SharePoint-style dashboard you can browse, with a download of the full pack (zip).

## What's in the pack
- 9 SharePoint-style sites with real Word, Excel, PowerPoint and PDF files: policies, board papers, performance reports, letters and templates.
- A linked database covering:
  - 1,840 homes and 6,900 repairs;
  - damp and mould cases tracked against Awaab's Law;
  - complaints under the Complaint Handling Code;
  - Tenant Satisfaction Measures survey responses;
  - rent accounts, voids and building safety checks.
- Communications: emails (including three shared mailboxes with a triage key), Teams chats, meetings with transcripts and recaps, scanned documents and photos.
- Trainer materials: personas, scenario cards and an answer key.
- PnP PowerShell scripts that provision the sites into a Microsoft 365 tenant.

## How it's built
The `spec/` folder holds the JSON world model, datasets and content. The builder in `tools/fictional-company` renders it into the pack. A GitHub Actions workflow rebuilds and publishes the site on every push.

```
pip install -r tools/fictional-company/requirements.txt
python tools/fictional-company/scripts/build_pack.py .
```

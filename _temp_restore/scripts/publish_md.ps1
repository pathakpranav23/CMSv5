Param(
  [string]$MdPath = "c:\project\CMSv5\Project Blueprint for CMS.md",
  [string]$NumberedMdPath = "c:\project\CMSv5\Project Blueprint for CMS.numbered.md",
  [string]$HtmlPath = "c:\project\CMSv5\publish.html",
  [string]$PdfPath = "c:\project\CMSv5\Project Blueprint for CMS.pdf"
)

if (-not (Test-Path -LiteralPath $MdPath)) { throw "Markdown not found: $MdPath" }

# Number headings (H2/H3) like 1., 1.1, etc.
$lines = Get-Content -LiteralPath $MdPath
$h2 = 0; $h3 = 0
$outLines = New-Object System.Collections.Generic.List[string]
foreach ($line in $lines) {
  if ($line -match '^##\s+(.*)$' -and ($line -notmatch '^##\s*Table of Contents')) {
    $h2++ ; $h3 = 0
    $text = $Matches[1]
    $outLines.Add("## $h2. $text")
  } elseif ($line -match '^###\s+(.*)$') {
    $h3++
    $text = $Matches[1]
    $outLines.Add("### $h2.$h3 $text")
  } else {
    $outLines.Add($line)
  }
}
[IO.File]::WriteAllLines($NumberedMdPath,$outLines)

# Read numbered MD and embed to HTML using marked.js; build TOC client-side
$md = [IO.File]::ReadAllText($NumberedMdPath)
try { Add-Type -AssemblyName System.Web -ErrorAction Stop } catch {}
function HtmlEncode([string]$s) {
  try { return [System.Web.HttpUtility]::HtmlEncode($s) } catch { return [System.Security.SecurityElement]::Escape($s) }
}

$html = @"
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Project Blueprint for CMS</title>
  <link rel="icon" href="favicon.ico" />
  <style>
    body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; margin: 32px; color: #222; }
    h1,h2,h3 { margin-top: 1.2em; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; }
    th, td { border: 1px solid #ddd; padding: 8px; }
    th { background: #f7f7f7; }
    #toc { border: 1px solid #eee; padding: 12px; background: #fafafa; }
    #toc ul { list-style: none; padding-left: 0; }
    #toc li { margin: 6px 0; }
    .sub { margin-left: 16px; }
    @page { margin: 20mm; }
    @media print { a[href^="#"]::after { content: ""; } }
  </style>
  <script src="https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"></script>
</head>
<body>
  <div id="toc"><strong>Table of Contents</strong><ul id="toc-list"></ul></div>
  <div id="content"></div>
  <textarea id="md-src" style="display:none">$(HtmlEncode($md))</textarea>
  <script>
    const src = document.getElementById('md-src').value;
    const escapeId = s => s.toLowerCase().replace(/[^a-z0-9\s\.\-]/g,'').replace(/\s+/g,'-');
    const renderer = new marked.Renderer();
    renderer.heading = function (text, level) {
      const id = escapeId(text);
      return `<h${level} id="${id}">${text}</h${level}>`;
    };
    marked.setOptions({ renderer });
    document.getElementById('content').innerHTML = marked.parse(src);
    // Build TOC from h2/h3
    const toc = document.getElementById('toc-list');
    document.querySelectorAll('#content h2, #content h3').forEach(h => {
      const li = document.createElement('li');
      if (h.tagName.toLowerCase() === 'h3') li.className = 'sub';
      const a = document.createElement('a');
      a.textContent = h.textContent;
      a.href = `#${h.id}`;
      li.appendChild(a);
      toc.appendChild(li);
    });
  </script>
</body>
</html>
"@

[IO.File]::WriteAllText($HtmlPath,$html)

# Print to PDF using Microsoft Edge headless
$htmlUri = (New-Object System.Uri($HtmlPath)).AbsoluteUri
$edgeCandidates = @(
  (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
  (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe')
)
$edgeExe = $null
foreach ($p in $edgeCandidates) { if (Test-Path $p) { $edgeExe = $p; break } }
if ($edgeExe -eq $null) { Write-Warning 'Microsoft Edge not found. Skipping PDF export.'; return }

& $edgeExe --headless --disable-gpu --virtual-time-budget=5000 --print-to-pdf="$PdfPath" "$htmlUri"
Write-Output "Published HTML: $HtmlPath"
Write-Output "Exported PDF: $PdfPath"
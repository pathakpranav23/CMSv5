Param(
  [string]$DocXmlPath = "c:\project\CMSv5\_docx_blueprint\word\document.xml",
  [string]$OutPath = "c:\project\CMSv5\Project Blueprint for CMS.md"
)

$xml = [xml](Get-Content -LiteralPath $DocXmlPath)
$nsMgr = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
$nsMgr.AddNamespace('w','http://schemas.openxmlformats.org/wordprocessingml/2006/main')

function Get-Text([System.Xml.XmlNode] $node) {
  $texts = $node.SelectNodes('.//w:t',$nsMgr)
  if ($texts -eq $null) { return '' }
  $sb = New-Object System.Text.StringBuilder
  foreach ($t in $texts) { [void]$sb.Append($t.InnerText) }
  return $sb.ToString()
}

$lines = New-Object System.Collections.Generic.List[string]
$body = $xml.SelectSingleNode('/w:document/w:body',$nsMgr)

foreach ($child in $body.ChildNodes) {
  switch ($child.LocalName) {
    'p' {
      $text = Get-Text $child
      $text = ($text -replace '\r?\n',' ' -replace '\s+',' ').Trim()
      if ($text.Length -gt 0) { $lines.Add($text); $lines.Add('') }
    }
    'tbl' {
      $rows = $child.SelectNodes('./w:tr',$nsMgr)
      if ($rows -ne $null -and $rows.Count -gt 0) {
        $first = $true
        foreach ($row in $rows) {
          $cells = $row.SelectNodes('./w:tc',$nsMgr)
          $cellTexts = @()
          foreach ($cell in $cells) {
            $cellText = Get-Text $cell
            $cellText = ($cellText -replace '\r?\n',' ' -replace '\s+',' ').Trim()
            $cellTexts += $cellText
          }
          $lines.Add('| ' + ($cellTexts -join ' | ') + ' |')
          if ($first) {
            $first = $false
            $sepCells = @()
            for ($i=0; $i -lt $cells.Count; $i++) { $sepCells += '---' }
            $lines.Add('| ' + ($sepCells -join ' | ') + ' |')
          }
        }
        $lines.Add('')
      }
    }
  }
}

[System.IO.File]::WriteAllLines($OutPath,$lines)

Write-Output "Exported: $OutPath"
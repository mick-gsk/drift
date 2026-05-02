$srcRoot = Join-Path $PWD 'src/drift'
$metaRoot = Join-Path $PWD 'packages/drift/src/drift'

$srcFiles = Get-ChildItem $srcRoot -Recurse -File -Filter *.py | ForEach-Object {
  [PSCustomObject]@{
    Rel = $_.FullName.Substring($srcRoot.Length + 1).Replace('\\','/')
    Full = $_.FullName
  }
}
$metaFiles = Get-ChildItem $metaRoot -Recurse -File -Filter *.py | ForEach-Object {
  [PSCustomObject]@{
    Rel = $_.FullName.Substring($metaRoot.Length + 1).Replace('\\','/')
    Full = $_.FullName
  }
}

$srcMap = @{}
foreach($f in $srcFiles){ $srcMap[$f.Rel] = $f.Full }
$metaMap = @{}
foreach($f in $metaFiles){ $metaMap[$f.Rel] = $f.Full }

$srcOnly = @($srcFiles | Where-Object { -not $metaMap.ContainsKey($_.Rel) } | Select-Object -ExpandProperty Rel)
$metaOnly = @($metaFiles | Where-Object { -not $srcMap.ContainsKey($_.Rel) } | Select-Object -ExpandProperty Rel)
$both = @($srcFiles | Where-Object { $metaMap.ContainsKey($_.Rel) } | Select-Object -ExpandProperty Rel)

function IsStub([string]$path){
  $head = Get-Content $path -TotalCount 30 -ErrorAction SilentlyContinue
  if($null -eq $head){ return $false }
  $txt = ($head -join "`n")
  return ($txt -match 'Re-export stub')
}

$srcNonStub = @()
foreach($f in $srcFiles){ if(-not (IsStub $f.Full)){ $srcNonStub += $f.Rel } }
$srcOnlyNonStub = @()
foreach($rel in $srcOnly){ if(-not (IsStub $srcMap[$rel])){ $srcOnlyNonStub += $rel } }
$bothSrcNonStub = @()
foreach($rel in $both){ if(-not (IsStub $srcMap[$rel])){ $bothSrcNonStub += $rel } }

$srcNonStubByTop = $srcNonStub | Group-Object { ($_ -split '/')[0] } | Sort-Object Count -Descending | ForEach-Object {
  [PSCustomObject]@{ Top = $_.Name; Count = $_.Count }
}

$result = [PSCustomObject]@{
  total_src = $srcFiles.Count
  total_meta = $metaFiles.Count
  src_only = $srcOnly.Count
  meta_only = $metaOnly.Count
  both = $both.Count
  src_non_stub = $srcNonStub.Count
  src_only_non_stub = $srcOnlyNonStub.Count
  both_with_src_non_stub = $bothSrcNonStub.Count
  src_only_non_stub_sample = $srcOnlyNonStub | Sort-Object | Select-Object -First 80
  both_with_src_non_stub_sample = $bothSrcNonStub | Sort-Object | Select-Object -First 80
  src_non_stub_top_buckets = $srcNonStubByTop | Select-Object -First 25
}

$result | ConvertTo-Json -Depth 6 | Set-Content tmp_migration_audit.json
Get-Content tmp_migration_audit.json -Raw

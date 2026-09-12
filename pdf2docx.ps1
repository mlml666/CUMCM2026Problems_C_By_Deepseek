$ErrorActionPreference = "Stop"
$src = "E:\qq文件\CUMCM2026Problems\C题\C题.pdf"
$dst = "E:\qq文件\CUMCM2026Problems\C题\C题_converted.docx"
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($src, $false, $true)  # ConfirmConversions=false, ReadOnly=true
    # 12 = wdFormatXMLDocument (docx); OpenXML ensures text extractable
    $doc.SaveAs([ref]$dst, [ref]12)
    $pages = $doc.ComputeStatistics(2)  # wdStatisticPages
    $words = $doc.ComputeStatistics(0)
    Write-Output "PAGES=$pages WORDS=$words"
    $doc.Close($false)
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($doc) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    Write-Output "SAVED=$dst"
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
    if ($word) { $word.Quit() }
}

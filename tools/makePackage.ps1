Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-LateMin  # power shell is very inconvenient
Remove-Item -Force -Recurse Packages/CorrectLocalizationJP-GenShin  # power shell is very inconvenient
mkdir -Force Packages/CorrectLocalizationJP-LateMin
mkdir -Force Packages/CorrectLocalizationJP-GenShin
Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-LateMin
Copy-Item -Recurse -Force Modules/CLJP-Common/* Packages/CorrectLocalizationJP-GenShin
Copy-Item -Recurse -Force Modules/CLJP-Font-GenShinGothic/* Packages/CorrectLocalizationJP-GenShin
Copy-Item -Recurse -Force Modules/CLJP-Font-LateMin/* Packages/CorrectLocalizationJP-LateMin
Compress-Archive -Force Packages/CorrectLocalizationJP-GenShin Packages/CorrectLocalizationJP-GenShin.zip
Compress-Archive -Force Packages/CorrectLocalizationJP-LateMin Packages/CorrectLocalizationJP-LateMin.zip
Get-ChildItem Modules | ForEach-Object {
    if ( -not ($_.Name.Substring(0, 5) -eq 'CLJP-')){
        Write-Output $_.Name
        Compress-Archive -Force Modules/$($_.Name)/ Packages/$($_.Name)JP.zip
    }
}
Remove-Item -Force -Recurse Packages/CorrectTextJP
mkdir -Force Packages/CorrectTextJP
Get-ChildItem Modules | ForEach-Object {
    if ( -not ($_.Name.Substring(0, 5) -eq 'CLJP-')){
        Write-Output $_.Name
        Copy-Item -Force -Recurse Modules/$($_.Name) Packages/CorrectTextJP/
    }
}
Compress-Archive -Force Packages/CorrectTextJP Packages/CorrectTextJP.zip
BeforeAll {
    $scriptPath = Join-Path $PSScriptRoot '..\scripts\Test-Clipboard.ps1'
}

Describe 'Test-Clipboard script structure' {
    It 'exists' {
        Test-Path -LiteralPath $scriptPath | Should -BeTrue
    }

    It 'does not print the original clipboard content' {
        $content = Get-Content -LiteralPath $scriptPath -Raw
        $content | Should -Not -Match 'Write-Host\s+\$originalText'
    }

    It 'supports JSON evidence output' {
        $content = Get-Content -LiteralPath $scriptPath -Raw
        $content | Should -Match 'JsonOutput'
        $content | Should -Match 'ConvertTo-Json'
    }

    It 'uses SHA-256 for comparison evidence' {
        $content = Get-Content -LiteralPath $scriptPath -Raw
        $content | Should -Match 'SHA256'
    }
}

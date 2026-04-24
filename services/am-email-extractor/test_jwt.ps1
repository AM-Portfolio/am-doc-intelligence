$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjY2MDM5NTgsImlhdCI6MTc2NjYwMjE1OCwic3ViIjoiNjRkNWY2YzktOTUxNi00ZWNhLWFjNDUtYzczY2ZmZjdhOGVjIiwidXNlcm5hbWUiOiJzc2QyNjU4QGdtYWlsLmNvbSIsImVtYWlsIjoic3NkMjY1OEBnbWFpbC5jb20iLCJzY29wZXMiOlsicmVhZCIsIndyaXRlIl19.g6RsAyQztmRuiBWAn0T3cRMompiPJj-mR1uELJSdtpU"

$headers = @{
    'Authorization' = "Bearer $token"
}

Write-Host "`n=== Testing Gmail Status Endpoint ===`n"

try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8080/api/v1/gmail/status' -Headers $headers
    Write-Host "Status Code: $($response.StatusCode)"
    Write-Host "Response:`n$($response.Content)"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    }
}

Write-Host "`n=== Testing Gmail Connect Endpoint ===`n"

try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8080/api/v1/gmail/connect' -Headers $headers
    Write-Host "Status Code: $($response.StatusCode)"
    Write-Host "Response:`n$($response.Content)"
} catch {
    Write-Host "Error: $($_.Exception.Message)"
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)"
    }
}

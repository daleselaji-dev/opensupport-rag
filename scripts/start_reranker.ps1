param(
  [int]$Port = 23146,
  [string]$Model = "$env:USERPROFILE\.lmstudio\models\ggml-org\Qwen3-reranker-0.6B-Q8_0-GGUF\qwen3-reranker-0.6b-q8_0.gguf",
  [switch]$Cpu
)

$backend = if ($Cpu) {
  "$env:USERPROFILE\.lmstudio\extensions\backends\llama.cpp-win-x86_64-avx2-2.16.0"
} else {
  "$env:USERPROFILE\.lmstudio\extensions\backends\llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1"
}
$vendor = "$env:USERPROFILE\.lmstudio\extensions\backends\vendor\win-llama-cuda12-vendor-v2"
if (-not $Cpu) { $env:Path = "$backend;$vendor;$env:Path" }
$exe = Join-Path $backend 'llama-server.exe'
if (-not (Test-Path $exe)) { throw "llama-server.exe not found: $exe" }
if (-not (Test-Path $Model)) { throw "Reranker GGUF not found: $Model" }
$serverArgs = @('-m', $Model, '--embedding', '--pooling', 'rank', '--rerank', '--host', '127.0.0.1', '--port', $Port, '--ctx-size', '4096', '--ubatch-size', '4096')
if (-not $Cpu) { $serverArgs += @('--n-gpu-layers', '99') }
& $exe @serverArgs

﻿#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated task tracking for Spec-Flow implementation workflow

.DESCRIPTION
    Tracks task completion, updates tasks.md, and maintains progress state
    Following Claude Code best practices: git commit after EVERY working feature

.PARAMETER Action
    Action to perform: status, mark-done, mark-in-progress, next, summary

.PARAMETER TaskId
    Task ID (e.g., T001, T002) when marking specific tasks

.PARAMETER Notes
    Implementation notes to add when marking task complete

.PARAMETER Json
    Return results in JSON format for AI parsing

.EXAMPLE
    .\task-tracker.ps1 status -Json
    Get current task status in JSON format

.EXAMPLE
    .\task-tracker.ps1 mark-done -TaskId T001 -Notes "Created FastAPI structure, added auth middleware"
    Mark T001 as completed with implementation notes

.EXAMPLE
    .\task-tracker.ps1 next
    Get next available task to work on
#>

param(
    [Parameter(Mandatory)]
    [ValidateSet("status", "mark-done", "mark-in-progress", "next", "summary", "validate")]
    [string]$Action,

    [string]$TaskId,
    [string]$Notes = "",
    [switch]$Json,
    [string]$FeatureDir = ""
)

# Set strict mode for better error handling
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Constants following Claude Code best practices
$MAX_PARALLEL_TASKS = 2  # Stop building one mega task - many specialized ones
$TASK_PATTERN = '^\s*-?\s*\[\s*(.?)\s*\]\s*(T\d+)(.*)$'
$COMPLETION_PATTERN = '^\s*\s*(.+)$'

function Get-FeatureDirectory {
    if ($FeatureDir) { return $FeatureDir }

    # Find the most recent feature directory
    $specsDir = Join-Path $PWD ".spec-flow" "memory" "specs"
    if (-not (Test-Path $specsDir)) {
        throw "No specs directory found. Run /spec-flow first."
    }

    $latestFeature = Get-ChildItem $specsDir -Directory |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (-not $latestFeature) {
        throw "No feature directories found in specs."
    }

    return $latestFeature.FullName
}

function Get-TasksFile {
    $featureDir = Get-FeatureDirectory
    $tasksFile = Join-Path $featureDir "tasks.md"

    if (-not (Test-Path $tasksFile)) {
        throw "No tasks.md found in $featureDir. Run /tasks first."
    }

    return $tasksFile
}

function Parse-TasksFile {
    param([string]$TasksFile)

    $content = Get-Content $TasksFile -Raw
    $lines = Get-Content $TasksFile
    $tasks = @()
    $currentTask = $null

    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]

        # Match task line: - [ ] T001 Description or - [X] T001 Description
        if ($line -match $TASK_PATTERN) {
            # Save previous task if exists
            if ($currentTask) {
                $tasks += $currentTask
            }

            $status = $matches[1]
            $taskId = $matches[2]
            $description = $matches[3].Trim()

            # Determine task status
            $isCompleted = $status -eq 'X' -or $status -eq 'x'
            $isInProgress = $status -eq '~' -or $status -eq 'P'
            $isParallel = $description -match '\[P\]'

            # Extract file paths from description
            $filePaths = @()
            if ($description -match '`([^`]+)`') {
                $filePaths = $matches[1] -split '\s*,\s*'
            }

            $currentTask = @{
                Id = $taskId
                Description = $description
                IsCompleted = $isCompleted
                IsInProgress = $isInProgress
                IsParallel = $isParallel
                FilePaths = $filePaths
                LineNumber = $i + 1
                CompletionNotes = @()
            }
        }
        # Match completion notes:  Description
        elseif ($currentTask -and $line -match $COMPLETION_PATTERN) {
            $currentTask.CompletionNotes += $matches[1].Trim()
        }
    }

    # Add last task
    if ($currentTask) {
        $tasks += $currentTask
    }

    return $tasks
}

function Get-TaskStatus {
    $tasksFile = Get-TasksFile
    $tasks = Parse-TasksFile $tasksFile

    $completed = $tasks | Where-Object { $_.IsCompleted }
    $inProgress = $tasks | Where-Object { $_.IsInProgress }
    $pending = $tasks | Where-Object { -not $_.IsCompleted -and -not $_.IsInProgress }

    $status = @{
        FeatureDir = Get-FeatureDirectory
        TasksFile = $tasksFile
        TotalTasks = $tasks.Count
        CompletedCount = $completed.Count
        InProgressCount = $inProgress.Count
        PendingCount = $pending.Count
        CompletedTasks = $completed | ForEach-Object { @{ Id = $_.Id; Description = $_.Description; Notes = $_.CompletionNotes } }
        InProgressTasks = $inProgress | ForEach-Object { @{ Id = $_.Id; Description = $_.Description; FilePaths = $_.FilePaths } }
        NextAvailableTasks = Get-NextAvailableTasks $tasks
        ParallelSafetyCheck = Test-ParallelSafety $inProgress
    }

    return $status
}

function Get-NextAvailableTasks {
    param([array]$AllTasks)

    # Get tasks that can be started (not completed, not in progress, dependencies met)
    $availableTasks = @()
    $completedIds = ($AllTasks | Where-Object { $_.IsCompleted }).Id
    $inProgressIds = ($AllTasks | Where-Object { $_.IsInProgress }).Id

    foreach ($task in $AllTasks) {
        if ($task.IsCompleted -or $task.IsInProgress) { continue }

        # For now, simple dependency: tasks should be done in order unless parallel
        $canStart = $true

        # If this is a non-parallel task, check if previous tasks are done
        if (-not $task.IsParallel) {
            $taskIndex = [array]::IndexOf($AllTasks.Id, $task.Id)
            for ($i = 0; $i -lt $taskIndex; $i++) {
                $prevTask = $AllTasks[$i]
                if (-not $prevTask.IsCompleted -and -not $prevTask.IsParallel) {
                    $canStart = $false
                    break
                }
            }
        }

        if ($canStart) {
            # Determine recommended agent and MCP tools based on task characteristics
            $recommendedAgent = Get-RecommendedAgent $task.Description $task.FilePaths
            $mcpTools = Get-RecommendedMcpTools $task.Description $task.FilePaths

            $availableTasks += @{
                Id = $task.Id
                Description = $task.Description
                IsParallel = $task.IsParallel
                FilePaths = $task.FilePaths
                Priority = if ($task.IsParallel) { "Low" } else { "High" }
                RecommendedAgent = $recommendedAgent
                McpTools = $mcpTools
            }
        }
    }

    return $availableTasks
}

function Get-RecommendedAgent {
    param([string]$Description, [array]$FilePaths)

    # Analyze file paths for agent routing
    foreach ($path in $FilePaths) {
        if ($path -match "apps/api") { return "backend-dev" }
        if ($path -match "apps/web") { return "frontend-shipper" }
        if ($path -match "contracts/") { return "contracts-sdk" }
        if ($path -match "migrations|alembic") { return "database-architect" }
        if ($path -match "\.github/workflows") { return "ci-cd-release" }
    }

    # Analyze description for task type
    if ($Description -match "test|spec") { return "qa-test" }
    if ($Description -match "debug|fix|error") { return "debugger" }
    if ($Description -match "coverage") { return "coverage-enhancer" }
    if ($Description -match "database|schema|migration") { return "database-architect" }

    return "general-purpose"
}

function Get-RecommendedMcpTools {
    param([string]$Description, [array]$FilePaths)

    $mcpTools = @()

    # Frontend tasks need Chrome DevTools
    if ($FilePaths -match "apps/web" -or $Description -match "frontend|ui|component") {
        $mcpTools += @("mcp__chrome-devtools__performance_start_trace", "mcp__chrome-devtools__take_screenshot")
    }

    # Testing tasks need Chrome DevTools and IDE
    if ($Description -match "test|e2e|accessibility") {
        $mcpTools += @("mcp__chrome-devtools__take_snapshot", "mcp__chrome-devtools__click", "mcp__ide__getDiagnostics")
    }

    # CI/CD tasks need GitHub MCP
    if ($Description -match "ci|cd|release|deploy" -or $FilePaths -match "\.github") {
        $mcpTools += @("mcp__github__run_workflow", "mcp__github__create_release", "mcp__github__create_pull_request")
    }

    # Debug tasks need comprehensive MCP tools
    if ($Description -match "debug|fix|error") {
        $mcpTools += @("mcp__chrome-devtools__list_console_messages", "mcp__ide__getDiagnostics", "mcp__chrome-devtools__get_network_request")
    }

    # Contract tasks need GitHub MCP
    if ($FilePaths -match "contracts/" -or $Description -match "api|contract|sdk") {
        $mcpTools += @("mcp__github__create_or_update_file", "mcp__github__search_code")
    }

    return $mcpTools
}

function Test-ParallelSafety {
    param([array]$InProgressTasks)

    if ($InProgressTasks.Count -le $MAX_PARALLEL_TASKS) {
        return @{ Safe = $true; Message = "Within parallel task limit ($($InProgressTasks.Count)/$MAX_PARALLEL_TASKS)" }
    }

    # Check for file conflicts
    $allFiles = @()
    foreach ($task in $InProgressTasks) {
        $allFiles += $task.FilePaths
    }

    $duplicates = $allFiles | Group-Object | Where-Object { $_.Count -gt 1 }
    if ($duplicates) {
        return @{
            Safe = $false
            Message = "File conflicts detected: $($duplicates.Name -join ', ')"
            ConflictingFiles = $duplicates.Name
        }
    }

    return @{
        Safe = $false
        Message = "Too many parallel tasks ($($InProgressTasks.Count)/$MAX_PARALLEL_TASKS)"
    }
}

function Update-TaskStatus {
    param(
        [string]$TaskId,
        [string]$NewStatus,
        [string]$Notes = ""
    )

    $tasksFile = Get-TasksFile
    $content = Get-Content $tasksFile
    $updated = $false

    for ($i = 0; $i -lt $content.Count; $i++) {
        if ($content[$i] -match $TASK_PATTERN -and $matches[2] -eq $TaskId) {
            $description = $matches[3]
            $content[$i] = "- [$NewStatus] $TaskId$description"

            # Add completion notes if marking as done
            if ($NewStatus -eq 'X' -and $Notes) {
                $noteLines = $Notes -split ';' | ForEach-Object { "     $($_.Trim())" }
                $insertIndex = $i + 1

                # Insert notes after the task line
                for ($j = $noteLines.Count - 1; $j -ge 0; $j--) {
                    $content = $content[0..($insertIndex-1)] + $noteLines[$j] + $content[$insertIndex..($content.Count-1)]
                }
            }

            $updated = $true
            break
        }
    }

    if (-not $updated) {
        throw "Task $TaskId not found in tasks.md"
    }

    # Write updated content
    Set-Content $tasksFile $content -Encoding UTF8

    return @{
        Success = $true
        TaskId = $TaskId
        NewStatus = $NewStatus
        Message = "Task $TaskId marked as $(switch ($NewStatus) { 'X' {'completed'}; '~' {'in progress'}; ' ' {'pending'} })"
        Notes = $Notes
    }
}

function Get-TaskSummary {
    $tasksFile = Get-TasksFile
    $tasks = Parse-TasksFile $tasksFile

    $phases = @{
        Setup = $tasks | Where-Object { $_.Description -match 'setup|configure|initialize' }
        Tests = $tasks | Where-Object { $_.Description -match 'test|spec' }
        Implementation = $tasks | Where-Object { $_.Description -match 'implement|create|build' -and $_.Description -notmatch 'test' }
        Integration = $tasks | Where-Object { $_.Description -match 'integrate|connect|middleware' }
        Polish = $tasks | Where-Object { $_.Description -match 'polish|performance|documentation|accessibility' }
    }

    $summary = @{
        OverallProgress = [math]::Round(($tasks | Where-Object { $_.IsCompleted }).Count / $tasks.Count * 100, 1)
        PhaseProgress = @{}
        RecentlyCompleted = ($tasks | Where-Object { $_.IsCompleted } | Select-Object -Last 5)
        BlockedTasks = @()
        Recommendations = @()
    }

    # Calculate phase progress
    foreach ($phase in $phases.Keys) {
        $phaseTasks = $phases[$phase]
        if ($phaseTasks.Count -gt 0) {
            $completed = ($phaseTasks | Where-Object { $_.IsCompleted }).Count
            $summary.PhaseProgress[$phase] = @{
                Completed = $completed
                Total = $phaseTasks.Count
                Percentage = [math]::Round($completed / $phaseTasks.Count * 100, 1)
            }
        }
    }

    # Add recommendations based on Claude Code best practices
    $inProgress = $tasks | Where-Object { $_.IsInProgress }
    if ($inProgress.Count -gt $MAX_PARALLEL_TASKS) {
        $summary.Recommendations += "Stop building one mega task - reduce parallel tasks to $MAX_PARALLEL_TASKS max"
    }

    $nextTests = $tasks | Where-Object { -not $_.IsCompleted -and $_.Description -match 'test' } | Select-Object -First 1
    $nextImpl = $tasks | Where-Object { -not $_.IsCompleted -and $_.Description -match 'implement' -and $_.Description -notmatch 'test' } | Select-Object -First 1

    if ($nextTests -and $nextImpl) {
        $summary.Recommendations += "Write tests BEFORE code - complete $($nextTests.Id) before $($nextImpl.Id)"
    }

    return $summary
}

function Validate-TasksFile {
    $tasksFile = Get-TasksFile
    $tasks = Parse-TasksFile $tasksFile
    $issues = @()

    # Check for TDD violations
    $testTasks = $tasks | Where-Object { $_.Description -match 'test' }
    $implTasks = $tasks | Where-Object { $_.Description -match 'implement' -and $_.Description -notmatch 'test' }

    foreach ($impl in $implTasks) {
        $relatedTest = $testTasks | Where-Object {
            $_.Description -match ($impl.Description -replace 'implement|create|build', 'test')
        }

        if ($relatedTest -and $impl.IsCompleted -and -not $relatedTest.IsCompleted) {
            $issues += "TDD Violation: $($impl.Id) completed but related test $($relatedTest.Id) not done"
        }
    }

    # Check parallel task safety
    $inProgress = $tasks | Where-Object { $_.IsInProgress }
    $safetyCheck = Test-ParallelSafety $inProgress
    if (-not $safetyCheck.Safe) {
        $issues += "Parallel Safety: $($safetyCheck.Message)"
    }

    # Check for missing file paths
    $tasksWithoutPaths = $tasks | Where-Object { $_.FilePaths.Count -eq 0 -and -not $_.Description -match 'setup|configure' }
    if ($tasksWithoutPaths) {
        $issues += "Missing file paths in tasks: $($tasksWithoutPaths.Id -join ', ')"
    }

    return @{
        Valid = $issues.Count -eq 0
        Issues = $issues
        TaskCount = $tasks.Count
        Recommendations = if ($issues.Count -eq 0) { @("Tasks file structure looks good") } else { @("Fix issues before implementation") }
    }
}

# Main execution
try {
    switch ($Action) {
        "status" {
            $result = Get-TaskStatus
        }
        "mark-done" {
            if (-not $TaskId) { throw "TaskId required for mark-done action" }
            $result = Update-TaskStatus -TaskId $TaskId -NewStatus 'X' -Notes $Notes
        }
        "mark-in-progress" {
            if (-not $TaskId) { throw "TaskId required for mark-in-progress action" }
            $result = Update-TaskStatus -TaskId $TaskId -NewStatus '~'
        }
        "next" {
            $status = Get-TaskStatus
            $result = @{
                NextTasks = $status.NextAvailableTasks
                CurrentInProgress = $status.InProgressTasks
                Recommendation = if ($status.NextAvailableTasks.Count -gt 0) {
                    "Start with: $($status.NextAvailableTasks[0].Id)"
                } else {
                    "No available tasks - check dependencies"
                }
            }
        }
        "summary" {
            $result = Get-TaskSummary
        }
        "validate" {
            $result = Validate-TasksFile
        }
    }

    if ($Json) {
        $result | ConvertTo-Json -Depth 10
    } else {
        $result | Format-Table -AutoSize
    }

} catch {
    $errorDetails = @{
        Success = $false
        Error = $_.Exception.Message
        Action = $Action
        Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    }

    if ($Json) {
        $errorDetails | ConvertTo-Json
    } else {
        Write-Error $errorDetails.Error
    }
    exit 1
}


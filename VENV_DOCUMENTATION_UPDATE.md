# Virtual Environment Documentation Update

## Date
November 7, 2025

## Summary
Updated all documentation to include comprehensive virtual environment setup instructions, making it the recommended approach for installing and running the team-reports MCP server.

## Motivation
User requested virtual environment setup instructions be added to the documentation. Virtual environments are best practice for Python projects as they:
- Isolate project dependencies
- Prevent version conflicts
- Keep system Python clean
- Make projects more reproducible

## Files Modified

### 1. README.md

#### Quick Start Section (Step 1)
**Added:**
- Detailed virtual environment setup instructions
- Both macOS/Linux and Windows activation commands
- Clear labeling of "Recommended" vs "Not Recommended"
- Note about using venv Python path in MCP configuration

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

#### MCP Configuration Section (Step 4)
**Added:**
- Separate configurations for "With Virtual Environment" and "Without Virtual Environment"
- Both Cursor and VS Code examples
- Clear path differences (`venv/bin/python3` vs `python3`)
- Updated GITHUB_TOKEN in all examples

**Cursor Example (with venv):**
```json
{
  "mcpServers": {
    "team-reports": {
      "type": "stdio",
      "command": "/full/path/to/team-reports-mcp-server/venv/bin/python3",
      ...
    }
  }
}
```

#### Start Server Section (Step 5)
**Added:**
- Note about activating virtual environment first
- Example activation command

```bash
# If using virtual environment, activate it first
source venv/bin/activate  # On macOS/Linux

# Start the server
python3 server.py
```

#### Troubleshooting Section
**Enhanced:**
- Updated "Module not found" error section with venv-specific instructions
- Added new "Virtual Environment Issues" section with:
  - How to ensure MCP uses correct Python
  - How to recreate broken venv
  - Windows-specific activation command
  - How to verify venv is active
- Updated "Cursor/VS Code doesn't see the server" with venv path example

**New Section:**
```
6. Virtual Environment Issues
   - If MCP can't find modules: Ensure command in MCP config points to venv/bin/python3
   - If activation fails: Recreate venv (rm -rf venv && python3 -m venv venv)
   - On Windows: Use venv\Scripts\activate instead of source venv/bin/activate
   - Check venv is active: which python3 should show path to venv
```

### 2. WEEKLY_REPORTS_QUICKSTART.md

#### Installation Section (Step 1)
**Added:**
- "With Virtual Environment (Recommended)" subsection
- "Without Virtual Environment" subsection  
- Explanation of why virtual environments are beneficial

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
```

#### MCP Configuration Section (Step 6)
**Added:**
- Separate examples for with/without virtual environment
- Clear labeling and path differences
- Important notes about absolute paths

#### Common Issues Section
**Added:**
- New "Virtual environment issues" troubleshooting section
- Commands to check if venv is active
- How to recreate venv
- Windows-specific instructions

## Configuration Examples Provided

### Virtual Environment Setup
```bash
cd team-reports-mcp-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### MCP Configuration (Cursor)
```json
"command": "/full/path/to/team-reports-mcp-server/venv/bin/python3"
```

### MCP Configuration (VS Code)
```json
"command": "/full/path/to/team-reports-mcp-server/venv/bin/python3"
```

## Key Points Emphasized

1. **Virtual environment is recommended** throughout all documentation
2. **Clear labeling** - "With Virtual Environment (Recommended)" vs "Without Virtual Environment"
3. **Platform-specific instructions** - macOS/Linux vs Windows activation
4. **MCP integration** - How to configure MCP clients to use venv Python
5. **Troubleshooting** - Common venv issues and solutions
6. **Verification** - How to check if venv is active

## Benefits for Users

### Clarity
- ✅ Clear step-by-step instructions for both approaches
- ✅ Platform-specific commands provided
- ✅ Consistent formatting across all documentation

### Best Practices
- ✅ Virtual environment clearly marked as recommended
- ✅ Explains why virtual environments are beneficial
- ✅ Shows correct MCP configuration for both scenarios

### Troubleshooting
- ✅ Dedicated section for venv issues
- ✅ Commands to verify venv is working
- ✅ Instructions to fix broken venv
- ✅ Platform-specific troubleshooting

### Complete Coverage
- ✅ Setup instructions
- ✅ MCP configuration
- ✅ Testing commands
- ✅ Troubleshooting
- ✅ Both documentation files updated

## What Users See Now

### In Quick Start
1. **Step 1:** Install with venv (recommended) or without
2. **Step 4:** Configure MCP with venv path or system Python
3. **Step 5:** Activate venv before starting server

### In Troubleshooting
- Dedicated section for venv issues
- Commands to verify and fix venv problems
- Platform-specific guidance

### In Quick Start Guide
- Same comprehensive coverage
- Focused on getting started quickly
- Clear recommendations

## Verification

✅ No linter errors in updated files  
✅ Consistent formatting throughout  
✅ All code examples use proper markdown  
✅ Platform differences clearly marked  
✅ Both recommended and alternative paths shown  

## Migration Path

### For New Users
- Follow the "With Virtual Environment (Recommended)" path
- Clear instructions from start to finish
- MCP configuration examples provided

### For Existing Users (Without Venv)
- Can continue using current setup
- Documentation shows how to migrate if desired
- No breaking changes

### For Existing Users (With Venv)
- Documentation now matches their setup
- Troubleshooting section helps with issues
- MCP configuration examples match their needs

## Summary

All documentation has been comprehensively updated to:
1. Make virtual environment setup the recommended approach
2. Provide clear instructions for both venv and non-venv setups
3. Show correct MCP configuration for each approach
4. Include troubleshooting for common venv issues
5. Support both Windows and macOS/Linux platforms

Users now have complete guidance for setting up and using the team-reports MCP server with best practices built in.


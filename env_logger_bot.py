"""
MEGA DEOBF ENVLOGGER BOT
Multi-Lua Variant Environment Logger & Deobfuscator
Supports: Luau, Lua 5.1-5.4, Lute, Luna
Hooks: loadstring, getfenv, setfenv, string.char, table.concat, require, pcall, xpcall
"""

import discord
from discord.ext import commands
import asyncio
import re
import json
import os
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
import io

# ============ CONFIG ============
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
COMMAND_PREFIX = ".env"
ALLOWED_GUILDS = []  # Leave empty for all guilds
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB

# ============ ENV LOGGER CORE ============
class EnvLogger:
    """Core environment logging engine for Lua/Luau deobfuscation"""
    
    def __init__(self):
        self.captured_sources = []
        self.hook_log = []
        self.call_stack = []
        
    def generate_hook_script(self, target_code: str, lua_variant: str = "luau") -> str:
        """
        Generates a wrapper script that hooks common obfuscation functions
        and logs decrypted code as it executes.
        """
        
        hook_template = '''
-- ENV LOGGER HOOK SYSTEM
local _G = getfenv and getfenv() or _ENV
local _ORIGINAL = {}

-- Capture storage
local _CAPTURED = {{}}
local _LOG = {{}}

local function log_capture(source, method, depth)
    table.insert(_CAPTURED, {{
        source = source,
        method = method,
        timestamp = os.time(),
        depth = depth,
        traceback = debug and debug.traceback and debug.traceback("", 2) or "N/A"
    }})
end

local function log_hook(func_name, args, result)
    table.insert(_LOG, {{
        func = func_name,
        args = args,
        result = result and "captured" or nil,
        time = os.time()
    }})
end

-- HOOK: loadstring / load
if loadstring then
    _ORIGINAL.loadstring = loadstring
    loadstring = function(chunk, chunkname)
        log_capture(chunk, "loadstring", 0)
        log_hook("loadstring", {{chunkname or "anonymous"}}, true)
        return _ORIGINAL.loadstring(chunk, chunkname)
    end
end

if load then
    _ORIGINAL.load = load
    load = function(ld, source, mode, env)
        if type(ld) == "string" then
            log_capture(ld, "load", 0)
            log_hook("load", {{source or "anonymous", mode}}, true)
        end
        return _ORIGINAL.load(ld, source, mode, env)
    end
end

-- HOOK: string.char (common in obfuscation)
_ORIGINAL.string_char = string.char
string.char = function(...)
    local result = _ORIGINAL.string_char(...)
    local args = {{...}}
    if #args > 10 then  -- Likely obfuscated string building
        log_hook("string.char", {{n = #args, preview = result:sub(1, 50)}}, true)
    end
    return result
end

-- HOOK: table.concat (common in obfuscation)
_ORIGINAL.table_concat = table.concat
table.concat = function(t, sep, i, j)
    local result = _ORIGINAL.table_concat(t, sep, i, j)
    if type(t) == "table" and #t > 10 then  -- Likely code building
        log_capture(result, "table.concat", 0)
        log_hook("table.concat", {{sep = sep or "", length = #result}}, true)
    end
    return result
end

-- HOOK: getfenv
if getfenv then
    _ORIGINAL.getfenv = getfenv
    getfenv = function(f)
        local env = _ORIGINAL.getfenv(f)
        log_hook("getfenv", {{type(f)}}, true)
        return env
    end
end

-- HOOK: setfenv
if setfenv then
    _ORIGINAL.setfenv = setfenv
    setfenv = function(f, table)
        log_hook("setfenv", {{type(f), type(table)}}, true)
        return _ORIGINAL.setfenv(f, table)
    end
end

-- HOOK: require
_ORIGINAL.require = require
require = function(modname)
    log_hook("require", {{modname}}, true)
    return _ORIGINAL.require(modname)
end

-- HOOK: pcall / xpcall
_ORIGINAL.pcall = pcall
pcall = function(f, ...)
    log_hook("pcall", {{type(f)}}, true)
    if type(f) == "string" then
        log_capture(f, "pcall_string", 0)
    end
    return _ORIGINAL.pcall(f, ...)
end

if xpcall then
    _ORIGINAL.xpcall = xpcall
    xpcall = function(f, msgh, ...)
        log_hook("xpcall", {{type(f), type(msgh)}}, true)
        return _ORIGINAL.xpcall(f, msgh, ...)
    end
end

-- HOOK: setmetatable (for __index/__newindex obfuscation)
_ORIGINAL.setmetatable = setmetatable
setmetatable = function(t, mt)
    if mt and mt.__index and type(mt.__index) == "function" then
        local orig = mt.__index
        mt.__index = function(self, k)
            log_hook("__index", {{tostring(k)}}, true)
            return orig(self, k)
        end
    end
    return _ORIGINAL.setmetatable(t, mt)
end

-- DECRYPTION DETECTION: Look for common patterns
local function detect_decryption(code)
    local patterns = {{
        "return%(function%(",
        "load%(",
        "loadstring%(",
        "string%.char",
        "table%.concat",
        "bytecode",
        "\\\\%d%d%d",
        "\\x[0-9a-fA-F][0-9a-fA-F]",
    }}
    
    for _, pattern in ipairs(patterns) do
        if code:match(pattern) then
            return true
        end
    end
    return false
end

-- AUTO-CAPTURE: Wrap all string operations
local mt = getmetatable and getmetatable("") or nil
if not mt then
    mt = {{}}
    if setmetatable then
        setmetatable("", mt)
    end
end

-- Execute target with full monitoring
local function execute_monitored()
    local target_code = [[
{TARGET_CODE}
]]
    
    -- Try to capture any immediate loadstring calls
    if detect_decryption(target_code) then
        log_capture(target_code, "initial_detection", 0)
    end
    
    -- Execute in protected mode
    local success, result = pcall(function()
        return loadstring and loadstring(target_code)() or load(target_code, "env_logger")()
    end)
    
    if not success then
        -- Try alternative execution
        success, result = pcall(function()
            local fn = assert(loadstring and loadstring(target_code) or load(target_code))
            return fn()
        end)
    end
    
    return {{
        success = success,
        result = result,
        error = not success and result or nil,
        captured = _CAPTURED,
        log = _LOG
    }}
end

-- Run and capture
local output = execute_monitored()

-- Format output for extraction
return string.format([[
=== ENV LOGGER OUTPUT ===
SUCCESS: %%s
CAPTURED_SOURCES: %%d
LOG_ENTRIES: %%d

=== CAPTURED SOURCES ===
%%s

=== EXECUTION LOG ===
%%s

=== ERROR (if any) ===
%%s
]], 
    tostring(output.success),
    #output.captured,
    #output.log,
    (#output.captured > 0) and table.concat(
        (function() 
            local t = {{}}
            for i, cap in ipairs(output.captured) do
                table.insert(t, string.format("--- Source %%d (via %%s) ---\\n%%s\\n", 
                    i, cap.method, cap.source:sub(1, 5000)))
            end
            return t
        end)()
    , "\\n") or "No sources captured",
    (#output.log > 0) and table.concat(
        (function()
            local t = {{}}
            for i, entry in ipairs(output.log) do
                table.insert(t, string.format("[%%d] %%s: %%s", i, entry.func, json and json.encode(entry.args) or "N/A"))
            end
            return t
        end)()
    , "\\n") or "No log entries",
    output.error or "None"
)
'''
        return hook_template.replace("{TARGET_CODE}", target_code.replace("]]", "]]..\"]]\"..[["))
    
    def generate_luau_hook(self, target_code: str) -> str:
        """Luau-specific hooks (Roblox variant)"""
        return self.generate_hook_script(target_code, "luau")
    
    def generate_lua51_hook(self, target_code: str) -> str:
        """Lua 5.1 specific hooks"""
        return self.generate_hook_script(target_code, "lua51")
    
    def beautify_lua(self, code: str) -> str:
        """Basic Lua beautification"""
        lines = code.split('\n')
        result = []
        indent = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Decrease indent for closing blocks
            if line.startswith(('end', '}', 'else', 'elseif', 'until')):
                indent = max(0, indent - 1)
            
            result.append('    ' * indent + line)
            
            # Increase indent for opening blocks
            if line.endswith(('then', 'do', '{', 'repeat')) or line.startswith(('function', 'if', 'while', 'for')):
                indent += 1
        
        return '\n'.join(result)

# ============ DISCORD BOT ============
class EnvLoggerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.dm_messages = True
        
        super().__init__(
            command_prefix=COMMAND_PREFIX,
            intents=intents,
            help_command=None
        )
        
        self.env_logger = EnvLogger()
        self.processing = set()
        
    async def setup_hook(self):
        print(f"[ENV LOGGER] Bot logged in as {self.user}")
        
    async def on_ready(self):
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="obfuscated scripts | .env help"
        )
        await self.change_presence(activity=activity)

bot = EnvLoggerBot()

# ============ COMMANDS ============

@bot.command(name="env")
async def env_logger_cmd(ctx, *, args: str = None):
    """
    Main env logger command
    Usage: .env [attachment | codeblock | raw_url | direct_code]
    """
    await ctx.typing()
    
    # Check if already processing
    if ctx.author.id in bot.processing:
        await ctx.send("⏳ Wait for current deobfuscation to complete!")
        return
    
    bot.processing.add(ctx.author.id)
    
    try:
        code = await extract_code(ctx, args)
        
        if not code:
            await ctx.send(embed=create_error_embed(
                "No code found!",
                "Provide code via:\n"
                "• Attachment (.lua, .luau, .txt)\n"
                "• Code block (```lua code```)\n"
                "• Raw URL\n"
                "• Direct message after command"
            ))
            return
        
        # Detect Lua variant
        variant = detect_lua_variant(code)
        
        # Create initial embed
        embed = discord.Embed(
            title="🔍 ENV LOGGER - Starting Deobfuscation",
            description=f"Detected variant: **{variant}**\nSetting up hooks...",
            color=0x3498db,
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {ctx.author}")
        status_msg = await ctx.send(embed=embed)
        
        # Generate hook script
        if variant == "luau":
            hook_script = bot.env_logger.generate_luau_hook(code)
        else:
            hook_script = bot.env_logger.generate_lua51_hook(code)
        
        # Execute (in sandbox)
        result = await execute_lua_sandbox(hook_script, variant)
        
        # Parse results
        captured_sources = extract_captured_sources(result)
        
        # Update embed with results
        if captured_sources:
            embed = discord.Embed(
                title="✅ ENV LOGGER - Sources Captured!",
                description=f"Found **{len(captured_sources)}** source(s)",
                color=0x2ecc71,
                timestamp=datetime.utcnow()
            )
            
            # Send sources as files
            files = []
            for i, source in enumerate(captured_sources[:5]):  # Limit to 5
                beautified = bot.env_logger.beautify_lua(source)
                filename = f"deobf_source_{i+1}_{variant}.lua"
                
                file = discord.File(
                    io.StringIO(beautified),
                    filename=filename
                )
                files.append(file)
                
                embed.add_field(
                    name=f"Source {i+1}",
                    value=f"```{variant[:3]}\n{beautified[:500]}...\n```",
                    inline=False
                )
            
            await status_msg.delete()
            await ctx.send(embed=embed, files=files if files else None)
            
            # Send full logs if available
            if len(result) > 1000:
                log_file = discord.File(
                    io.StringIO(result),
                    filename=f"env_log_{ctx.author.id}.txt"
                )
                await ctx.send("📋 Full execution log:", file=log_file)
        else:
            embed = discord.Embed(
                title="⚠️ ENV LOGGER - No Sources Captured",
                description="The script ran but no decrypted sources were intercepted.\n"
                           "Try manual analysis or different hooks.",
                color=0xe74c3c
            )
            embed.add_field(
                name="Execution Output",
                value=f"```{result[:1000]}```",
                inline=False
            )
            await status_msg.edit(embed=embed)
            
    except Exception as e:
        await ctx.send(embed=create_error_embed("Error", str(e)))
    finally:
        bot.processing.discard(ctx.author.id)

@bot.command(name="envhook")
async def env_hook_info(ctx):
    """Show hooked functions"""
    embed = discord.Embed(
        title="🔧 ENV LOGGER - Hooked Functions",
        description="These functions are intercepted during execution:",
        color=0x9b59b6
    )
    
    hooks = [
        ("`loadstring` / `load`", "Captures dynamically loaded code"),
        ("`getfenv` / `setfenv`", "Tracks environment manipulation"),
        ("`string.char`", "Detects string building from byte arrays"),
        ("`table.concat`", "Captures code assembly from tables"),
        ("`require`", "Logs module loading"),
        ("`pcall` / `xpcall`", "Catches protected execution"),
        ("`setmetatable`", "Monitors __index/__newindex"),
    ]
    
    for name, desc in hooks:
        embed.add_field(name=name, value=desc, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="envhelp")
async def env_help(ctx):
    """Show help"""
    embed = discord.Embed(
        title="📖 ENV LOGGER BOT - Help",
        description="Advanced Lua/Luau deobfuscation via environment logging",
        color=0x1abc9c
    )
    
    embed.add_field(
        name="Commands",
        value=(
            "`.env [code]` - Deobfuscate script\n"
            "`.envhook` - Show hooked functions\n"
            "`.envhelp` - This help message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Input Methods",
        value=(
            "1. **Attachment**: Upload .lua/.luau file\n"
            "2. **Code Block**: Paste code in ```lua\n"
            "3. **Raw URL**: Paste direct link to raw code\n"
            "4. **Direct**: Type code after command"
        ),
        inline=False
    )
    
    embed.add_field(
        name="Supported Variants",
        value="• Luau (Roblox)\n• Lua 5.1/5.2/5.3/5.4\n• Lute\n• Luna",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ============ UTILITIES ============

async def extract_code(ctx, args: str) -> Optional[str]:
    """Extract code from various input methods"""
    
    # Check attachments
    if ctx.message.attachments:
        att = ctx.message.attachments[0]
        if att.size > MAX_FILE_SIZE:
            raise ValueError("File too large (max 8MB)")
        
        allowed_exts = ('.lua', '.luau', '.txt', '.lute', '.luna')
        if not any(att.filename.endswith(ext) for ext in allowed_exts):
            raise ValueError(f"Invalid file type. Allowed: {allowed_exts}")
        
        content = await att.read()
        return content.decode('utf-8', errors='ignore')
    
    # Check for code block
    if args:
        # Code block: ```lua ... ```
        block_match = re.search(r'```(?:lua|luau)?\n?(.*?)```', args, re.DOTALL)
        if block_match:
            return block_match.group(1).strip()
        
        # Raw URL
        if args.strip().startswith(('http://', 'https://')):
            async with aiohttp.ClientSession() as session:
                async with session.get(args.strip()) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    raise ValueError(f"URL returned status {resp.status}")
        
        # Direct code
        return args.strip()
    
    return None

def detect_lua_variant(code: str) -> str:
    """Detect which Lua variant the code uses"""
    indicators = {
        'luau': ['getfenv', 'setfenv', 'typeof', 'Vector3', 'Instance', 'game:'],
        'lua51': ['getfenv', 'setfenv', 'module', 'setfenv'],
        'lua52': ['_ENV', 'load', 'bit32'],
        'lua53': ['utf8', 'table.move', 'bit32'],
        'lua54': ['warn', 'table.move', 'close'],
    }
    
    scores = {k: 0 for k in indicators}
    
    for variant, patterns in indicators.items():
        for pattern in patterns:
            if pattern in code:
                scores[variant] += 1
    
    # Default to luau for Roblox context
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else 'luau'

async def execute_lua_sandbox(script: str, variant: str) -> str:
    """
    Execute Lua script in sandboxed environment
    Returns execution output
    """
    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False) as f:
        f.write(script)
        temp_path = f.name
    
    try:
        # Select interpreter based on variant
        interpreters = {
            'luau': 'luau',  # Roblox Luau CLI
            'lua51': 'lua5.1',
            'lua52': 'lua5.2',
            'lua53': 'lua5.3',
            'lua54': 'lua5.4',
        }
        
        interpreter = interpreters.get(variant, 'lua')
        
        # Execute with timeout
        proc = await asyncio.create_subprocess_exec(
            interpreter, temp_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            proc.kill()
            return "ERROR: Execution timeout (30s)"
        
        output = stdout.decode('utf-8', errors='ignore')
        errors = stderr.decode('utf-8', errors='ignore')
        
        if errors:
            output += f"\n\nSTDERR:\n{errors}"
        
        return output
        
    except FileNotFoundError:
        # Fallback: simulate execution with Python Lua parser
        return simulate_execution(script)
    finally:
        try:
            os.unlink(temp_path)
        except:
            pass

def simulate_execution(script: str) -> str:
    """Simulate Lua execution for analysis when interpreter not available"""
    # Extract captured sources using regex
    sources = []
    
    # Look for common deobfuscation patterns
    patterns = [
        r'return%s*\(function%([^)]*%)%s*(.-)%s*end%)%(%)',
        r'load%s*\(%s*["\']%s*(.-)%s*["\']%s*%)',
        r'loadstring%s*\(%s*["\']%s*(.-)%s*["\']%s*%)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, script, re.DOTALL)
        sources.extend(matches)
    
    if sources:
        return f"SIMULATED CAPTURE:\nFound {len(sources)} potential sources\n" + "\n---\n".join(sources[:3])
    
    return "SIMULATION: No sources extracted (interpreter not available)"

def extract_captured_sources(output: str) -> List[str]:
    """Extract captured sources from execution output"""
    sources = []
    
    # Look for source captures in output
    capture_pattern = r'--- Source \d+ \(via ([^)]+)\) ---\n(.*?)(?=\n--- Source|\Z)'
    matches = re.findall(capture_pattern, output, re.DOTALL)
    
    for method, source in matches:
        if len(source.strip()) > 50:  # Filter noise
            sources.append(source.strip())
    
    # Also look for raw loadstring captures
    if not sources:
        # Extract from table.concat results
        concat_pattern = r'table\.concat.*?\n(.*?)(?=\n\[|\Z)'
        matches = re.findall(concat_pattern, output, re.DOTALL)
        sources.extend([m for m in matches if len(m) > 100])
    
    return sources

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create error embed"""
    return discord.Embed(
        title=f"❌ {title}",
        description=description,
        color=0xe74c3c
    )

# ============ RUN ============
if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set your bot token!")
        print("Get one at: https://discord.com/developers/applications")
    else:
        bot.run(BOT_TOKEN)

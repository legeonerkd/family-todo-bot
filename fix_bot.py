from pathlib import Path

p = Path("bot.py")
text = p.read_text(encoding="utf-8")

log_block = """# =====================================================
# HELPERS: ACTIVITY LOG
# =====================================================

async def log_action(family_id: int, user_id: int, action: str):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO activity_log (family_id, user_id, action) "
            "VALUES ($1, $2, $3)",
            family_id, user_id, action
        )

"""

marker = "# =====================================================\n# UI"

if log_block not in text:
    text = text.replace(marker, log_block + marker)

p.write_text(text, encoding="utf-8")
print("OK: log_action inserted")

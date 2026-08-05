import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

# --- MINI SERVIDOR WEB PARA MANTENER EL BOT 24/7 ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot VPN WoW Online 24/7")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Inicia el servidor web en segundo plano
threading.Thread(target=run_web_server, daemon=True).start()

# --- CONFIGURACIÓN DEL BOT DE DISCORD ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

FIXED_USERS = ["monkhal", "Randy", "Ethan", "Vilum", "Aldo"]
user_status = {name: {"status": "OFF", "vpn": "Sin asignar"} for name in FIXED_USERS}
guests_status = {}

def create_dashboard_embed():
    embed = discord.Embed(
        title="🛡️ Panel de Control de VPN Mullvad",
        description="Presiona los botones para cambiar tu estado **ON / OFF**.",
        color=discord.Color.blue()
    )

    fixed_text = ""
    for name in FIXED_USERS:
        info = user_status[name]
        if info["status"] == "ON":
            fixed_text += f"🟢 **{name}** | VPN: `{info['vpn']}` | **[ON]**\n"
        else:
            fixed_text += f"🔴 **{name}** | VPN: *Sin usar* | **[OFF]**\n"

    embed.add_field(name="👥 Usuarios Fijos", value=fixed_text, inline=False)

    guest_text = ""
    if not guests_status:
        guest_text = "*No hay invitados registrados.*"
    else:
        for g_name, info in guests_status.items():
            if info["status"] == "ON":
                guest_text += f"🟢 **{g_name}** *(Invitado)* | VPN: `{info['vpn']}` | **[ON]**\n"
            else:
                guest_text += f"🔴 **{g_name}** *(Invitado)* | VPN: `{info['vpn']}` | **[OFF]**\n"

    embed.add_field(name="🎟️ Usuarios Invitados", value=guest_text, inline=False)
    embed.set_footer(text="WoW Carrys VPN Tracker • Actualizado en tiempo real")
    return embed

class OnModal(discord.ui.Modal, title="Conectarse a VPN (ON)"):
    nombre = discord.ui.TextInput(label="Nombre de usuario", placeholder="Ej: monkhal, Randy...", required=True)
    vpn_user = discord.ui.TextInput(label="Usuario / Nombre de VPN en uso", placeholder="Ej: little rabbit...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        input_name = self.nombre.value.strip()
        vpn_val = self.vpn_user.value.strip()

        match_fixed = next((f for f in FIXED_USERS if f.lower() == input_name.lower()), None)

        if match_fixed:
            user_status[match_fixed] = {"status": "ON", "vpn": vpn_val}
            msg = f"🟢 **{match_fixed}** ahora está en **ON** con la VPN `{vpn_val}`."
        else:
            guests_status[input_name] = {"status": "ON", "vpn": vpn_val}
            msg = f"🟢 **{input_name}** (Invitado) ahora está en **ON** con la VPN `{vpn_val}`."

        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(msg, ephemeral=True)

class OffModal(discord.ui.Modal, title="Desconectarse de VPN (OFF)"):
    nombre = discord.ui.TextInput(label="Nombre de usuario", placeholder="Ej: monkhal, Randy...", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        input_name = self.nombre.value.strip()

        match_fixed = next((f for f in FIXED_USERS if f.lower() == input_name.lower()), None)

        if match_fixed:
            user_status[match_fixed] = {"status": "OFF", "vpn": "Sin asignar"}
            msg = f"🔴 **{match_fixed}** se ha puesto en **OFF**."
        else:
            match_guest = next((g for g in guests_status if g.lower() == input_name.lower()), None)
            if match_guest:
                guests_status[match_guest]["status"] = "OFF"
                msg = f"🔴 **{match_guest}** (Invitado) se ha puesto en **OFF**."
            else:
                msg = f"⚠️ No se encontró al usuario '{input_name}'."

        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(msg, ephemeral=True)

class VPNControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Conectar (ON)", style=discord.ButtonStyle.green, custom_id="vpn_on_btn")
    async def btn_on(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OnModal())

    @discord.ui.button(label="🔴 Desconectar (OFF)", style=discord.ButtonStyle.red, custom_id="vpn_off_btn")
    async def btn_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OffModal())

@bot.event
async def on_ready():
    print(f"Bot activo correctamente como: {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def panel_vpn(ctx):
    await ctx.message.delete()
    embed = create_dashboard_embed()
    await ctx.send(embed=embed, view=VPNControlView())

bot.run(os.environ.get("DISCORD_TOKEN"))

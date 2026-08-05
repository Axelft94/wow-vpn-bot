import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

# --- MINI SERVIDOR WEB PARA MANTENER EL BOT 24/7 EN RENDER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot VPN WoW Online 24/7")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- CONFIGURACIÓN DEL BOT DE DISCORD ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Lista de usuarios fijos
FIXED_USERS = ["monkhal", "Randy", "Ethan", "Vilum", "Aldo"]

# Memoria de usuarios
user_status = {name: {"status": "OFF", "vpn": "Sin asignar"} for name in FIXED_USERS}
guests_status = {}

def create_dashboard_embed():
    embed = discord.Embed(
        title="🛡️ Panel de Control de VPN Mullvad",
        description="Selecciona tu usuario fijo en el menú o usa los botones de invitados.",
        color=discord.Color.blue()
    )

    # Usuarios Fijos (Conserva la VPN siempre)
    fixed_text = ""
    for name in FIXED_USERS:
        info = user_status[name]
        if info["status"] == "ON":
            fixed_text += f"🟢 **{name}** | VPN: `{info['vpn']}` | **[ON]**\n"
        else:
            fixed_text += f"🔴 **{name}** | VPN: `{info['vpn']}` | **[OFF]**\n"

    embed.add_field(name="👥 Usuarios Fijos", value=fixed_text, inline=False)

    # Usuarios Invitados (Solo se muestran los activos)
    guest_text = ""
    if not guests_status:
        guest_text = "*No hay invitados activos.*"
    else:
        for g_name, info in guests_status.items():
            guest_text += f"🟢 **{g_name}** *(Invitado)* | VPN: `{info['vpn']}` | **[ON]**\n"

    embed.add_field(name="🎟️ Usuarios Invitados", value=guest_text, inline=False)
    embed.set_footer(text="WoW Carrys VPN Tracker • Actualizado en tiempo real")
    return embed

# Ventana para Editar la VPN de un Usuario Fijo
class EditFixedVpnModal(discord.ui.Modal):
    def __init__(self, user_name: str):
        super().__init__(title=f"Editar VPN de {user_name}")
        self.user_name = user_name
        
        current_vpn = user_status[user_name]["vpn"]
        default_val = current_vpn if current_vpn != "Sin asignar" else ""
        
        self.nueva_vpn = discord.ui.TextInput(
            label=f"Nombre de VPN para {user_name}",
            placeholder="Ej: holy cicada, silent-tiger...",
            default=default_val,
            required=True
        )
        self.add_item(self.nueva_vpn)

    async def on_submit(self, interaction: discord.Interaction):
        vpn_val = self.nueva_vpn.value.strip()
        user_status[self.user_name]["vpn"] = vpn_val
        
        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"✏️ La VPN de **{self.user_name}** se cambió a `{vpn_val}`.", ephemeral=True)

# Ventana para Invitado ON
class GuestOnModal(discord.ui.Modal, title="Conectar Invitado (ON)"):
    nombre = discord.ui.TextInput(
        label="Nombre de Invitado",
        placeholder="Ej: sylph, invitado1...",
        required=True
    )
    vpn_user = discord.ui.TextInput(
        label="Usuario / Nombre de VPN en uso",
        placeholder="Ej: little rabbit...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        g_name = self.nombre.value.strip()
        vpn_val = self.vpn_user.value.strip()
        guests_status[g_name] = {"status": "ON", "vpn": vpn_val}

        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"🟢 Invitado **{g_name}** conectado en **ON** con VPN `{vpn_val}`.", ephemeral=True)

# Ventana para Invitado OFF
class GuestOffModal(discord.ui.Modal, title="Desconectar Invitado (OFF)"):
    nombre = discord.ui.TextInput(
        label="Nombre de Invitado a desconectar",
        placeholder="Ej: sylph...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        g_name = self.nombre.value.strip()
        match_guest = next((g for g in guests_status if g.lower() == g_name.lower()), None)

        if match_guest:
            del guests_status[match_guest]
            msg = f"🔴 Invitado **{match_guest}** se ha puesto en **OFF** y fue eliminado de la lista."
        else:
            msg = f"⚠️ No se encontró al invitado '{g_name}' en la lista activa."

        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(msg, ephemeral=True)

# Menú Desplegable para seleccionar Usuario Fijo
class FixedUserSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=name, description=f"Usuario Fijo: {name}")
            for name in FIXED_USERS
        ]
        super().__init__(placeholder="👇 Selecciona un usuario fijo...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        self.view.selected_user = self.values[0]
        await interaction.response.defer()

# Vista Principal con Controles
class VPNControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_user = None
        self.add_item(FixedUserSelect())

    @discord.ui.button(label="🟢 Fijo ON", style=discord.ButtonStyle.green, row=1)
    async def btn_fixed_on(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("⚠️ Primero debes seleccionar tu nombre en el menú desplegable.", ephemeral=True)
            return

        user_status[self.selected_user]["status"] = "ON"
        vpn_curr = user_status[self.selected_user]["vpn"]
        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"🟢 **{self.selected_user}** pasa a **ON** (VPN: `{vpn_curr}`).", ephemeral=True)

    @discord.ui.button(label="🔴 Fijo OFF", style=discord.ButtonStyle.red, row=1)
    async def btn_fixed_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("⚠️ Primero debes seleccionar tu nombre en el menú desplegable.", ephemeral=True)
            return

        user_status[self.selected_user]["status"] = "OFF"
        vpn_curr = user_status[self.selected_user]["vpn"]
        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"🔴 **{self.selected_user}** pasa a **OFF** (VPN: `{vpn_curr}`).", ephemeral=True)

    @discord.ui.button(label="✏️ Editar VPN", style=discord.ButtonStyle.secondary, row=1)
    async def btn_fixed_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_user:
            await interaction.response.send_message("⚠️ Primero debes seleccionar un usuario fijo en el menú desplegable.", ephemeral=True)
            return

        await interaction.response.send_modal(EditFixedVpnModal(self.selected_user))

    @discord.ui.button(label="🎟️ Invitado ON", style=discord.ButtonStyle.primary, row=2)
    async def btn_guest_on(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuestOnModal())

    @discord.ui.button(label="🎟️ Invitado OFF", style=discord.ButtonStyle.gray, row=2)
    async def btn_guest_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuestOffModal())

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

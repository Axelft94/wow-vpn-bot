import os
import json
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
DATA_FILE = "vpn_data.json"

# Guardar selección temporal por usuario de Discord
user_selections = {}

# --- SISTEMA DE PERSISTENCIA (GUARDAR EN ARCHIVO JSON) ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                u_status = data.get("user_status", {})
                g_status = data.get("guests_status", {})
                for u in FIXED_USERS:
                    if u not in u_status:
                        u_status[u] = {"status": "OFF", "vpn": "Sin asignar"}
                return u_status, g_status
        except Exception as e:
            print("Error al cargar datos:", e)
    
    u_status = {name: {"status": "OFF", "vpn": "Sin asignar"} for name in FIXED_USERS}
    g_status = {}
    return u_status, g_status

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"user_status": user_status, "guests_status": guests_status}, f, indent=4)
    except Exception as e:
        print("Error al guardar datos:", e)

user_status, guests_status = load_data()

def create_dashboard_embed():
    embed = discord.Embed(
        title="🛡️ Panel de Control de VPN Mullvad",
        description="Selecciona tu usuario fijo en el menú o usa los botones de invitados.",
        color=discord.Color.blue()
    )

    # Usuarios Fijos
    fixed_text = ""
    for name in FIXED_USERS:
        info = user_status.get(name, {"status": "OFF", "vpn": "Sin asignar"})
        if info["status"] == "ON":
            fixed_text += f"🟢 **{name}** | VPN: `{info['vpn']}` | **[ON]**\n"
        else:
            fixed_text += f"🔴 **{name}** | VPN: `{info['vpn']}` | **[OFF]**\n"

    embed.add_field(name="👥 Usuarios Fijos", value=fixed_text, inline=False)

    # Usuarios Invitados
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
        
        current_vpn = user_status.get(user_name, {}).get("vpn", "Sin asignar")
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
        save_data()
        
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
        save_data()

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
            save_data()
            msg = f"🔴 Invitado **{match_guest}** se ha puesto en **OFF** y fue eliminado de la lista."
        else:
            msg = f"⚠️ No se encontró al invitado '{g_name}' en la lista activa."

        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(msg, ephemeral=True)

# Menú Desplegable con Custom ID Persistente
class FixedUserSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, value=name, description=f"Usuario Fijo: {name}")
            for name in FIXED_USERS
        ]
        super().__init__(
            placeholder="👇 Selecciona un usuario fijo...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="vpn_fixed_user_select"
        )

    async def callback(self, interaction: discord.Interaction):
        user_selections[interaction.user.id] = self.values[0]
        await interaction.response.send_message(
            f"✅ Has seleccionado a **{self.values[0]}**. Ahora presiona **Fijo ON**, **Fijo OFF** o **Editar VPN**.",
            ephemeral=True
        )

# Vista Principal Persistente
class VPNControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FixedUserSelect())

    @discord.ui.button(label="🟢 Fijo ON", style=discord.ButtonStyle.green, row=1, custom_id="btn_fixed_on")
    async def btn_fixed_on(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_user = user_selections.get(interaction.user.id)
        if not selected_user:
            await interaction.response.send_message("⚠️ Primero debes seleccionar tu nombre en el menú desplegable.", ephemeral=True)
            return

        user_status[selected_user]["status"] = "ON"
        save_data()
        vpn_curr = user_status[selected_user]["vpn"]
        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"🟢 **{selected_user}** pasa a **ON** (VPN: `{vpn_curr}`).", ephemeral=True)

    @discord.ui.button(label="🔴 Fijo OFF", style=discord.ButtonStyle.red, row=1, custom_id="btn_fixed_off")
    async def btn_fixed_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_user = user_selections.get(interaction.user.id)
        if not selected_user:
            await interaction.response.send_message("⚠️ Primero debes seleccionar tu nombre en el menú desplegable.", ephemeral=True)
            return

        user_status[selected_user]["status"] = "OFF"
        save_data()
        vpn_curr = user_status[selected_user]["vpn"]
        embed = create_dashboard_embed()
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"🔴 **{selected_user}** pasa a **OFF** (VPN: `{vpn_curr}`).", ephemeral=True)

    @discord.ui.button(label="✏️ Editar VPN", style=discord.ButtonStyle.secondary, row=1, custom_id="btn_fixed_edit")
    async def btn_fixed_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        selected_user = user_selections.get(interaction.user.id)
        if not selected_user:
            await interaction.response.send_message("⚠️ Primero debes seleccionar un usuario fijo en el menú desplegable.", ephemeral=True)
            return

        await interaction.response.send_modal(EditFixedVpnModal(selected_user))

    @discord.ui.button(label="🎟️ Invitado ON", style=discord.ButtonStyle.primary, row=2, custom_id="btn_guest_on")
    async def btn_guest_on(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuestOnModal())

    @discord.ui.button(label="🎟️ Invitado OFF", style=discord.ButtonStyle.gray, row=2, custom_id="btn_guest_off")
    async def btn_guest_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(GuestOffModal())

@bot.event
async def on_ready():
    # Registramos la vista para que sea totalmente persistente tras reiniciar
    bot.add_view(VPNControlView())
    print(f"Bot activo correctamente como: {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def panel_vpn(ctx):
    await ctx.message.delete()
    embed = create_dashboard_embed()
    await ctx.send(embed=embed, view=VPNControlView())

bot.run(os.environ.get("DISCORD_TOKEN"))

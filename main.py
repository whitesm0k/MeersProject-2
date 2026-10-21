import discord
import os
from discord import app_commands, ui
from discord.ext import commands

# --- НАСТРОЙКИ ---
raw_channel_id = os.getenv("CHANNEL_ID", "0")
try:
    CHANNEL_ID = int(raw_channel_id)
except ValueError:
    print("⚠️ CHANNEL_ID не является числом. Устанавливаем в 0.")
    CHANNEL_ID = 0

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("❌ Критическая ошибка: Переменная окружения BOT_TOKEN не найдена!")

PRODUCTS = ["MeersExternal", "MeersMacro", "Другой"]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class TicketView(ui.View):
    def __init__(self, products):
        super().__init__(timeout=None)
        self.products = products
        
        # Уникальный ID, чтобы сбросить старые кнопки
        button = ui.Button(
            label="📩 Создать обращение",
            style=discord.ButtonStyle.blurple,
            custom_id="create_ticket_btn_v3" 
        )
        button.callback = self.create_ticket
        self.add_item(button)

    async def create_ticket(self, interaction: discord.Interaction):
        # ЗАЩИТА: Если ответ уже был дан (ошибка InteractionResponded), просто выходим
        if interaction.response.is_done():
            return

        try:
            modal = TicketModal(product_options=self.products)
            # Отправляем модалку как ЕДИНСТВЕННЫЙ ответ
            await interaction.response.send_modal(modal)
        except discord.errors.InteractionResponded:
            # Если вдруг Discord считает, что ответ уже есть - игнорируем
            pass
        except Exception as e:
            # Показываем ошибку пользователю, чтобы ты видел проблему
            await interaction.response.send_message(f"❌ Ошибка: {e}", ephemeral=True)

class TicketModal(ui.Modal, title="Создание тикета"):
    def __init__(self, product_options):
        super().__init__()
        
        self.category_select = ui.Select(
            placeholder="1. Тип обращения",
            options=[discord.SelectOption(label=opt) for opt in ["Проблема", "Вопрос", "Покупка"]],
            custom_id="category_select"
        )
        self.product_select = ui.Select(
            placeholder="2. Продукт",
            options=[discord.SelectOption(label=opt) for opt in product_options],
            custom_id="product_select"
        )
        self.comment_input = ui.TextInput(
            label="Комментарий",
            style=discord.TextStyle.long,
            placeholder="Опишите проблему...",
            required=False,
            max_length=1000
        )
        
        self.add_item(self.category_select)
        self.add_item(self.product_select)
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.response.is_done():
            return

        category = self.category_select.values if self.category_select.values else "Не указано"
        product = self.product_select.values if self.product_select.values else "Не указано"
        comment = self.comment_input.value if self.comment_input.value else "Без комментария"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        safe_name = interaction.user.name.replace(" ", "-")[:90]
        channel_name = f"ticket-{safe_name}"
        
        try:
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                reason=f"Тикет от {interaction.user}"
            )
            
            embed = discord.Embed(title="✅ Новый тикет создан", color=discord.Color.green())
            embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
            embed.add_field(name="Тип", value=category, inline=False)
            embed.add_field(name="Продукт", value=product, inline=False)
            embed.add_field(name="Комментарий", value=comment, inline=False)
            embed.set_footer(text=f"ID канала: {ticket_channel.id}")
            
            await ticket_channel.send(embed=embed)
            await interaction.response.send_message(f"Тикет создан: {ticket_channel.mention}", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ У бота нет прав на создание каналов!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка создания: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Бот запущен как {bot.user}')
    
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=1547655055673663619))
        print(f"✅ Синхронизировано команд: {len(synced)}")
    except Exception as e:
        print(f"⚠️ Ошибка синхронизации: {e}")
    
    view = TicketView(products=PRODUCTS)
    bot.add_view(view)
    
    if isinstance(CHANNEL_ID, int) and CHANNEL_ID != 0:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            welcome_text = "Добро пожаловать! Нажмите кнопку ниже для создания тикета."
            try:
                # Мы НЕ отправляем кнопку автоматически здесь, если есть риск дублирования.
                # Лучше использовать команду /sendticketbtn
                print(f"⚠️ Автоматическая отправка кнопки отключена для избежания дублей. Используйте /sendticketbtn")
            except Exception as e:
                print(f"❌ Ошибка: {e}")
        else:
            print(f"❌ Канал с ID {CHANNEL_ID} не найден.")
    else:
        print("⚠️ CHANNEL_ID не задан. Используйте /sendticketbtn для отправки кнопки.")

@bot.tree.command(name="sendticketbtn", description="Отправить кнопку тикета в текущий канал")
@app_commands.checks.has_permissions(administrator=True)
async def send_ticket_btn(interaction: discord.Interaction):
    welcome_text = "Нажмите кнопку ниже, чтобы создать тикет."
    view = TicketView(products=PRODUCTS)
    await interaction.response.send_message(content=welcome_text, view=view)

bot.run(TOKEN)

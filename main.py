import discord
import os
from discord import app_commands, ui
from discord.ext import commands

# --- НАСТРОЙКИ (АВТОМАТИЧЕСКОЕ ЧТЕНИЕ С ХОСТИНГА) ---

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
        button = ui.Button(
            label="📩 Создать обращение",
            style=discord.ButtonStyle.blurple,
            custom_id="create_ticket_btn"
        )
        button.callback = self.create_ticket
        self.add_item(button)

    async def create_ticket(self, interaction: discord.Interaction):
        # Сообщаем Discord, что бот обрабатывает запрос (защита от таймаута)
        await interaction.response.defer(ephemeral=True)
        
        # Создаем модальное окно
        modal = TicketModal(product_options=self.products)
        
        # ВАЖНО: Модальные окна отправляются ТОЛЬКО через response.send_modal
        await interaction.followup.send_modal(modal)


class TicketModal(ui.Modal, title="Создание тикета"):
    def __init__(self, product_options):
        super().__init__()
        self.category_select = ui.Select(
            placeholder="1. Проблема/Вопрос/Покупка?",
            options=[discord.SelectOption(label=opt) for opt in ["Проблема", "Вопрос", "Покупка"]],
            custom_id="category_select"
        )
        self.product_select = ui.Select(
            placeholder="2. Какой продукт вы выбираете?",
            options=[discord.SelectOption(label=opt) for opt in product_options],
            custom_id="product_select"
        )
        self.comment_input = ui.TextInput(
            label="3. Комментарий",
            style=discord.TextStyle.long,
            placeholder="Опишите подробнее...",
            required=False,
            max_length=1000
        )
        self.add_item(self.category_select)
        self.add_item(self.product_select)
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Защита от пустых значений (на случай ошибок)
        category = self.category_select.values if self.category_select.values else "Не указано"
        product = self.product_select.values if self.product_select.values else "Не указано"
        comment = self.comment_input.value if self.comment_input.value else "Без комментария"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel_name = f"ticket-{interaction.user.name}"
        
        try:
            ticket_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                category=None
            )
            embed = discord.Embed(title="Новый тикет", color=discord.Color.blue())
            embed.add_field(name="Пользователь", value=interaction.user.mention, inline=False)
            embed.add_field(name="Тип обращения", value=category, inline=False)
            embed.add_field(name="Продукт", value=product, inline=False)
            embed.add_field(name="Комментарий", value=comment, inline=False)
            embed.set_footer(text=f"ID тикета: {ticket_channel.id}")
            
            await ticket_channel.send(embed=embed)
            
            # Используем followup, так как response уже был использован при открытии модалки
            await interaction.followup.send(f"Тикет создан: {ticket_channel.mention}", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ У бота нет прав на создание каналов. Проверьте права роли бота.", ephemeral=True)
        except Exception as e:
            # ИСПРАВЛЕНО: добавлен правильный отступ
            await interaction.followup.send(f"❌ Ошибка создания тикета: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Бот запущен как {bot.user}')
    
    try:
        # Синхронизация команд (оставьте guild=... для одного сервера, или раскомментируйте sync() для всех)
        synced = await bot.tree.sync(guild=discord.Object(id=1547655055673663619))
        print(f"✅ Синхронизировано команд: {len(synced)}")
    except Exception as e:
        print(f"⚠️ Ошибка синхронизации команд: {e}")
    
    view = TicketView(products=PRODUCTS)
    bot.add_view(view)
    
    if isinstance(CHANNEL_ID, int) and CHANNEL_ID != 0:
        channel = bot.get_channel(CHANNEL_ID)
        print(f"Попытка отправки кнопки: CHANNEL_ID={CHANNEL_ID}, канал={channel}")
        
        if channel:
            welcome_text = (
                "Добро пожаловать! Нажмите кнопку ниже, чтобы написать тикет Тех.Поддержке с вопросом, "
                "проблемой или покупкой.\n\n"
                "**Важное примечание:** Не оставляйте оффтоп тикет, не агрессируйте на администрацию, "
                "не пишите тикет в шуточной форме. Спасибо!"
            )
            try:
                await channel.send(content=welcome_text, view=view)
                print(f"✅ Кнопка успешно отправлена в канал #{channel.name}")
            except discord.Forbidden:
                print(f"❌ Ошибка: У бота нет прав на отправку сообщений в канал #{channel.name}")
            except Exception as e:
                print(f"❌ Произошла ошибка при отправке кнопки: {e}")
        else:
            print(f"❌ Ошибка: Канал с ID {CHANNEL_ID} не найден.")
    else:
        print("⚠️ CHANNEL_ID не задан. Кнопка не будет отправлена автоматически.")

@bot.tree.command(name="sendticketbtn", description="Отправить кнопку создания тикета в текущий канал")
@app_commands.checks.has_permissions(administrator=True)
async def send_ticket_btn(interaction: discord.Interaction):
    welcome_text = (
        "Добро пожаловать! Нажмите кнопку ниже, чтобы написать тикет Тех.Поддержке с вопросом, "
        "проблемой или покупкой.\n\n"
        "**Важное примечание:** Не оставляйте оффтоп тикет, не агрессируйте на администрацию, "
        "не пишите тикет в шуточной форме. Спасибо!"
    )
    view = TicketView(products=PRODUCTS)
    await interaction.response.send_message(content=welcome_text, view=view)

bot.run(TOKEN)

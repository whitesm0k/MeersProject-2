import discord
import os
from discord import app_commands, ui
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
# tree = app_commands.CommandTree(bot)  <-- УДАЛЕНО

PRODUCTS = ["MeersExternal", "MeersMacro", "Другой"]

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
        category = self.category_select.values
        product = self.product_select.values
        comment = self.comment_input.value if self.comment_input.value else "Без комментария"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        channel_name = f"ticket-{interaction.user.name}"
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
        await interaction.response.send_message(f"Тикет создан: {ticket_channel.mention}", ephemeral=True)


class TicketView(ui.View):
    def __init__(self, products):
        super().__init__(timeout=None)
        self.products = products
        button = ui.Button(label="📩 Создать обращение", style=discord.ButtonStyle.blurple)
        button.callback = self.create_ticket
        self.add_item(button)

    async def create_ticket(self, interaction: discord.Interaction):
        modal = TicketModal(product_options=self.products)
        await interaction.response.send_modal(modal)


@bot.event
async def on_ready():
    print(f'Бот запущен как {bot.user}')
    await bot.tree.sync()  # <-- ИЗМЕНЕНО
    bot.add_view(TicketView(products=PRODUCTS))

@bot.event
async def on_ready():
    print(f'Бот запущен как {bot.user}')
    # Вариант 1: глобальная синхронизация (до 1 часа появления)
    # await bot.tree.sync()
    
    # Вариант 2: мгновенная синхронизация для конкретного сервера (рекомендуется)
    await bot.tree.sync(guild=discord.Object(id=1547655055673663619))  # <-- заменить на ID вашего сервера
    
    bot.add_view(TicketView(products=PRODUCTS))



@bot.tree.command(name="sendticketbtn", description="Отправить кнопку создания тикета в текущий канал")  # <-- ИЗМЕНЕНО
@app_commands.checks.has_permissions(administrator=True)
async def send_ticket_btn(interaction: discord.Interaction):
    welcome_text = (
        "Добро пожаловать! Нажмите кнопку ниже, чтобы написать тикет Тех.Поддержке с вопросом, "
        "проблемой или покупкой.\n\n"
        "**Важное примечание:** Не оставляйте оффтоп тикет, Не агрессируйте на администрацию, "
        "Не пишите тикет в шуточной форме. Спасибо!"
    )
    view = TicketView(products=PRODUCTS)
    await interaction.response.send_message(content=welcome_text, view=view)


TOKEN = os.getenv("BOT_TOKEN")
bot.run(TOKEN)

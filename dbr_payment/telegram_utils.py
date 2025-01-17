import requests
from django.conf import settings


def test_telegram_bot(bot_token=None, chat_id=None):
    """
    Utility function to test Telegram bot connectivity

    Args:
    - bot_token (str, optional): Telegram Bot Token.
      If not provided, will use settings.TELEGRAM_BOT_TOKEN
    - chat_id (str, optional): Telegram Chat ID.
      If not provided, will use the first chat_id argument

    Returns:
    dict: A dictionary with test results
    """
    # Get bot token from settings if not provided
    if not bot_token:
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

    if not bot_token:
        return {
            'success': False,
            'error': 'No Telegram Bot Token found. Please configure TELEGRAM_BOT_TOKEN in settings.'
        }

    # Endpoint for getting bot information
    get_me_url = f'https://api.telegram.org/bot{bot_token}/getMe'

    try:
        # Test bot token by getting bot information
        response = requests.get(get_me_url)
        response.raise_for_status()
        bot_info = response.json()

        # If chat_id is provided, attempt to send a test message
        if chat_id:
            send_message_url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
            message_params = {
                'chat_id': chat_id,
                'text': '🤖 This is a test message from your Django application!'
            }

            try:
                message_response = requests.post(send_message_url, json=message_params)
                message_response.raise_for_status()

                return {
                    'success': True,
                    'bot_username': bot_info['result']['username'],
                    'message_status': 'Sent successfully'
                }
            except requests.RequestException as message_error:
                return {
                    'success': False,
                    'bot_username': bot_info['result']['username'],
                    'error': f'Failed to send message: {str(message_error)}'
                }

        return {
            'success': True,
            'bot_username': bot_info['result']['username'],
            'message_status': 'Bot token valid, no message sent'
        }

    except requests.RequestException as e:
        return {
            'success': False,
            'error': f'Failed to connect to Telegram: {str(e)}'
        }


def debug_telegram_bot(company=None):
    """
    Debug Telegram bot for a specific company or globally

    Args:
    - company (Company, optional): Company instance to debug

    Returns:
    dict: Debugging information
    """
    from .models import Company

    # Use global bot token from settings
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)

    if company:
        # If a specific company is provided, use its chat ID
        chat_id = company.telegram_chat_id

        if not chat_id:
            return {
                'success': False,
                'error': f'No Telegram Chat ID found for company {company.name}'
            }

        return test_telegram_bot(bot_token, chat_id)

    # If no company is provided, do a global check
    # Attempt to find any company with a Telegram Chat ID
    companies_with_chat_id = Company.objects.exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id='')

    if not companies_with_chat_id.exists():
        return {
            'success': False,
            'error': 'No companies found with a Telegram Chat ID'
        }

    # Test with the first company's chat ID
    sample_company = companies_with_chat_id.first()

    return test_telegram_bot(bot_token, sample_company.telegram_chat_id)
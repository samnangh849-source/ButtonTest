const express = require('express');
const bodyParser = require('body-parser');
const TelegramBot = require('node-telegram-bot-api');

// --- ការកំណត់រចនាសម្ព័ន្ធ (Configuration) ---
const TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const RENDER_URL = process.env.RENDER_URL; // ឧ. https://your-app-name.onrender.com
const BOT_USERNAME = process.env.BOT_USERNAME; // ឧ. 'MyTestBot' (គ្មាន @)
const WEBHOOK_PATH = '/telegram-webhook';
const FULL_WEBHOOK_URL = `${RENDER_URL}${WEBHOOK_PATH}`;

// ពិនិត្យមើល Environment Variables
if (!TOKEN || !RENDER_URL || !BOT_USERNAME) {
    console.error('សូមប្រាកដថាអ្នកបានកំណត់ TELEGRAM_BOT_TOKEN, RENDER_URL, និង BOT_USERNAME នៅក្នុង Environment Variables។');
    process.exit(1);
}

const bot = new TelegramBot(TOKEN);

// --- ផ្នែក Bot Logic (ពិនិត្យ និងកែសម្រួលសារ) ---

// ប្រើ Webhook ជំនួស Polling សម្រាប់ Render.com
bot.setWebHook(FULL_WEBHOOK_URL);

const app = express();
app.use(bodyParser.json());

// ទទួល Webhook ពី Telegram
app.post(WEBHOOK_PATH, (req, res) => {
    bot.processUpdate(req.body);
    res.sendStatus(200);
});

console.log(`Bot កំពុងដំណើរការ... Webhook ត្រូវបានកំណត់ទៅ: ${FULL_WEBHOOK_URL}`);

// ត្រង Regex សម្រាប់ទម្រង់សាររបស់អ្នក
// ប្រើ Flag 's' ដើម្បីឱ្យ '.' អាចចាប់យក newline (\n) បាន
// [កែសម្រួល] នេះគឺជា REGEX ថ្មីដែលត្រូវនឹងទម្រង់សារពិតប្រាកដរបស់អ្នក
const orderRegex = /👤 អតិថិជន: (.*?)\n📞 លេខទូរស័ព្ទ: (.*?)\n📍 ទីតាំង: (.*?)\n(?:🏠 អាសយដ្ឋាន: (.*?)\n)?.*?-\s*សរុបចុងក្រោយ: \$(.*?)\n\s*(.*?)\n\n🚚 វិធីសាស្រ្តដឹកជញ្ជូន: (.*?)(?:\n|$)/s;

// ស្ដាប់រាល់សារទាំងអស់ (ទាំង message ក្នុង group និង channel post)
bot.on('message', (msg) => {
    // ហៅ function សម្រាប់ពិនិត្យ
    handlePotentialOrderMessage(msg);
});

bot.on('channel_post', (msg) => {
    // ហៅ function សម្រាប់ពិនិត្យ (ប្រសិនបើ Bot នៅក្នុង Channel)
    handlePotentialOrderMessage(msg);
});

async function handlePotentialOrderMessage(msg) {
    const chatId = msg.chat.id;
    const messageId = msg.message_id;
    const messageText = msg.text || msg.caption; // យក Text
    
    // 1. ពិនិត្យថាជាសារ Text
    if (!messageText) return;

    // 2. ពិនិត្យថាផ្ញើដោយ Bot ខ្លួនឯង
    // វិធីដែលល្អបំផុតគឺត្រូវដឹង ID របស់ Bot ខ្លួនឯង
    // យើងអាចប្រើ username ជាការប្រៀបធៀបបណ្ដោះអាសន្ន
    if (msg.from.username !== BOT_USERNAME || !msg.from.is_bot) {
        // console.log(`រំលងសារពី: ${msg.from.username}`);
        return;
    }

    // 3. ពិនិត្យមើលថាតើសារនេះមានប៊ូតុងរួចហើយឬនៅ
    if (msg.reply_markup) {
        // console.log(`រំលងសារ ${messageId} ព្រោះមានប៊ូតុងរួចហើយ`);
        return;
    }

    // 4. ពិនិត្យមើលទម្រង់សារដោយប្រើ Regex
    const match = messageText.match(orderRegex);

    if (match) {
        console.log(`រកឃើញសារបញ្ជាទិញដែលត្រូវគ្នា! Message ID: ${messageId}`);

        try {
            // ទាញយកទិន្នន័យពី Regex groups
            const [
                _, // ពេញ
                customerName,
                customerPhone,
                location,
                addressDetails = '', // ប្រើ '' ជា default បើไม่มี
                grandTotal,
                paymentStatus,
                shippingMethod
            ] = match.map(item => item ? item.trim() : ''); // Trim គ្រប់ទិន្នន័យ

            // 5. បង្កើត Object ទិន្នន័យ
            const data = {
                name: customerName,
                phone: customerPhone,
                loc: location,
                addr: addressDetails,
                total: grandTotal,
                payment: paymentStatus,
                shipping: shippingMethod,
            };

            // 6. បង្កើត URL សម្រាប់ព្រីន ដោយ encode ទិន្នន័យ
            const queryParams = new URLSearchParams();
            for (const key in data) {
                if (data[key]) { // បន្ថែមតែទិន្នន័យណាที่มี
                    queryParams.append(key, data[key]);
                }
            }
            
            const printUrl = `${RENDER_URL}/print?${queryParams.toString()}`;
            
            // 7. បង្កើត Inline Keyboard
            const inlineKeyboard = {
                inline_keyboard: [
                    [
                        {
                            text: '🖨️ ព្រីន Label (78x50mm)',
                            url: printUrl
                        }
                    ]
                ]
            };

            // 8. កែសម្រួលសារដើម ដើម្បីបន្ថែមប៊ូតុង
            await bot.editMessageReplyMarkup(inlineKeyboard, {
                chat_id: chatId,
                message_id: messageId
            });

            console.log(`បានបន្ថែមប៊ូតុងព្រីនទៅសារ ${messageId} ដោយជោគជ័យ។`);

        } catch (err) {
            console.error(`បរាជ័យក្នុងការកែសម្រួលសារ ${messageId}:`, err.response ? err.response.body : err.message);
        }
    } else {
        // [បន្ថែម] បង្ហាញ Log ប្រសិនបើរកមិនឃើញសារដែលត្រូវគ្នា
        // console.log(`សារ ${messageId} មិនត្រូវនឹងទម្រង់ Regex`);
    }
}


// --- ផ្នែក Web App សម្រាប់ព្រីន (Print Page) ---

app.get('/print', (req, res) => {
    // 1. យកទិន្នន័យពី Query Parameters
    const { name, phone, loc, addr, total, payment, shipping } = req.query;

    // 2. បង្កើត HTML សម្រាប់ Label
    const printHtml = `
        <!DOCTYPE html>
        <html lang="km">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Print Label</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Khmer&family=Roboto:wght@400;700&display=swap');
                
                body {
                    font-family: 'Khmer', 'Roboto', sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f0f0f0; /* ពណ៌ផ្ទៃខាងក្រៅ Label */
                }

                .label {
                    width: 78mm;
                    height: 50mm;
                    box-sizing: border-box; /* ធានាទំហំឲ្យបានត្រឹមត្រូវ */
                    padding: 4mm;
                    border: 1px dashed #999; /* បន្ទាត់សម្រាប់កាត់ (មិនបង្ហាញពេលព្រីន) */
                    background-color: #ffffff; /* ពណ៌ផ្ទៃ Label */
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }

                .label-header {
                    text-align: center;
                    font-weight: 700;
                    font-size: 10pt;
                    border-bottom: 1px solid #000;
                    padding-bottom: 2mm;
                }
                
                .label-content {
                    font-size: 10pt;
                    line-height: 1.5;
                }

                .label-content p {
                    margin: 0.5mm 0;
                }
                
                .label-content .phone {
                    font-size: 12pt;
                    font-weight: 700;
                }
                
                .label-footer {
                    border-top: 1px solid #000;
                    padding-top: 2mm;
                    font-size: 9pt;
                    font-weight: 700;
                    display: flex;
                    justify-content: space-between;
                }
                
                .payment-status {
                    font-size: 10pt;
                    font-weight: 700;
                    text-align: center;
                    margin-top: 1mm;
                    /* [កែសម្រួល] កែពណ៌ក្រហម/បៃតង ឱ្យកាន់តែប្រសើរ */
                    color: ${payment && (payment.includes('Paid') || payment.includes(' bez') || payment.includes('โอน')) ? 'green' : 'red'};
                }

                /* CSS សម្រាប់ពេលព្រីន */
                @media print {
                    body {
                        background-color: #ffffff;
                    }
                    .label {
                        border: none; /* លុបបន្ទាត់ពេលព្រីន */
                        margin: 0;
                        padding: 0; /* អាចត្រូវការកែសម្រួល */
                    }
                    /* លាក់ UI ផ្សេងៗ (បើមាន) */
                    .no-print {
                        display: none;
                    }
                }

                /* កំណត់ទំហំទំព័រពេលព្រីន */
                @page {
                    size: 78mm 50mm;
                    margin: 0;
                }
            </style>
        </head>
        <body>
            <div class="label">
                <div class="label-header">
                    <p style="margin: 0;">${name || 'N/A'}</p>
                    <p class="phone" style="margin: 0;">${phone || 'N/A'}</p>
                </div>

                <div class="label-content">
                    <p><strong>ទីតាំង:</strong> ${loc || 'N/A'}</p>
                    ${addr && addr !== '(មិនបានបញ្ជាក់)' ? `<p><strong>អាសយដ្ឋាន:</strong> ${addr}</p>` : ''}
                    <p class="payment-status">${payment || 'N/A'}</p>
                </div>

                <div class="label-footer">
                    <span>${shipping || 'N/A'}</span>
                    <span>សរុប: $${total || '0.00'}</span>
                </div>
            </div>

            <!-- ប៊ូតុងសម្រាប់ព្រីនម្ដងទៀត (មិនបង្ហាញពេលព្រីន) -->
            <button class="no-print" onclick="window.print()" style="margin: 10px; padding: 10px; font-size: 16px;">
                🖨️ ព្រីនម្ដងទៀត
            </button>

            <script>
                // បើកផ្ទាំង Print ដោយស្វ័យប្រវត្តិ
                window.onload = () => {
                    window.print();
                };
            </script>
        </body>
        </html>
    `;

    res.send(printHtml);
});


// --- ចាប់ផ្ដើម Server ---
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server កំពុងដំណើរការនៅលើ Port ${PORT}`);
});


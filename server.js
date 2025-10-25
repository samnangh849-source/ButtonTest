const express = require('express');
const bodyParser = require('body-parser');
const TelegramBot = require('node-telegram-bot-api');
require('dotenv').config();

const TOKEN = process.env.BOT_TOKEN;
const RENDER_URL = process.env.RENDER_URL; // ឧទាហរណ៍៖ https://your-app-name.onrender.com
const WEBHOOK_PATH = `/webhook/${TOKEN}`;
const FULL_WEBHOOK_URL = `${RENDER_URL}${WEBHOOK_PATH}`;

// --- 1. ការចាប់ផ្ដើម Bot និង Server ---

const bot = new TelegramBot(TOKEN);
const app = express();
app.use(bodyParser.json());

// កំណត់ Webhook
bot.setWebHook(FULL_WEBHOOK_URL).then(status => {
    console.log(`Webhook set to ${FULL_WEBHOOK_URL}: ${status}`);
}).catch(err => {
    console.error('Error setting webhook:', err);
});

// --- 2. មុខងារ Regex សម្រាប់ស្រង់ទិន្នន័យ ---

/**
 * ស្រង់ទិន្នន័យលម្អិតពីអត្ថបទសារ
 * @param {string} text - អត្ថបទសារពេញលេញ
 * @returns {object|null} - Object ផ្ទុកទិន្នន័យ ឬ null ប្រសិនបើមិនត្រូវទម្រង់
 */
function parseOrderDetails(text) {
    const regex = /👤 អតិថិជន: (.*)\n📞 លេខទូរស័ព្ទ: (.*)\n📍 ទីតាំង: (.*)\n🏠 អាសយដ្ឋាន: (.*)\n[\s\S]*?សរុបចុងក្រោយ: \$(.*)\n\s*(🟥|🟩) (.*) \(.*\)\n\n🚚 វិធីសាស្រ្តដឹកជញ្ជូន: (.*)/;
    const match = text.match(regex);

    if (!match) {
        return null;
    }

    let addressDetails = match[4].trim();
    if (addressDetails === '(មិនបានបញ្ជាក់)') {
        addressDetails = ''; // ទុកឲ្យនៅទទេ ប្រសិនបើមិនបានបញ្ជាក់
    }

    return {
        customerInfo: match[1].trim(), // នេះជា '23' នៅក្នុងឧទាហរណ៍
        customerPhone: match[2].trim(),
        location: match[3].trim(),
        addressDetails: addressDetails,
        grandTotal: match[5].trim(),
        paymentStatus: match[7].trim(), // ឧទាហរណ៍ 'COD'
        shippingMethod: match[8].trim(),
    };
}

// --- 3. ការបង្កើតប៊ូតុងព្រីន ---

/**
 * បង្កើត Inline Keyboard សម្រាប់ព្រីន
 * @returns {object} - Telegram Reply Markup Object
 */
function getPrintButtonMarkup() {
    return {
        inline_keyboard: [
            [
                {
                    text: '🖨️ ព្រីន Label (78x50mm)',
                    callback_data: 'print_label' // នេះជាអត្តសញ្ញាណសម្គាល់
                }
            ]
        ]
    };
}

// --- 4. ឡូហ្សិកគ្រប់គ្រង Webhook (សារចូល) ---

app.post(WEBHOOK_PATH, (req, res) => {
    bot.processUpdate(req.body);
    res.sendStatus(200);
});

// --- 5. ឡូហ្សិក Bot (Commands និង Actions) ---

// Command សម្រាប់សាកល្បងផ្ញើសារបញ្ជាទិញ (សម្រាប់សារថ្មី)
bot.onText(/\/sendorder/, async (msg) => {
    const chatId = msg.chat.id;
    const sampleOrderText = `✅សូមបងពិនិត្យលេខទូរស័ព្ទ និងទីតាំងម្ដងទៀតបង 🙏

👤 អតិថិជន: 23
📞 លេខទូរស័ព្ទ: 023
📍 ទីតាំង: Phnom Penh
🏠 អាសយដ្ឋាន: (មិនបានបញ្ជាក់)
🛍️ ផលិតផល:
  - Sample Product (x1) = $25.00

--------------------------------------
💰 សរុប:
  - តម្លៃទំនិញ: $25.00
  - សេវាដឹក: $0.00
  - សរុបចុងក្រោយ: $25.00
  🟥 COD (Unpaid)

🚚 វិធីសាស្រ្តដឹកជញ្ជូន: J&T
--------------------------------------
អរគុណបង🙏🥰`;

    try {
        // 1. ផ្ញើសារបញ្ជាទិញ
        const sentMessage = await bot.sendMessage(chatId, sampleOrderText);
        console.log('Order message sent, message_id:', sentMessage.message_id);

        // 2. ពិនិត្យមើលថាតើសារនោះត្រូវនឹងទម្រង់ដែរឬទេ
        const data = parseOrderDetails(sentMessage.text);
        
        if (data) {
            // 3. បើត្រូវ, Edit សារនោះភ្លាមៗដើម្បីបន្ថែមប៊ូតុង
            await bot.editMessageReplyMarkup(getPrintButtonMarkup(), {
                chat_id: chatId,
                message_id: sentMessage.message_id
            });
            console.log(`Added print button to NEW message ${sentMessage.message_id}`);
        }
    } catch (err) {
        console.error('Error in /sendorder flow:', err);
    }
});

// Command សម្រាប់បន្ថែមប៊ូតុងទៅសារចាស់ (ដោយការ Reply)
bot.onText(/\/addprintbutton/, async (msg) => {
    const chatId = msg.chat.id;

    // ពិនិត្យមើលថាតើ user បាន Reply ទៅសារណាមួយឬអត់
    if (!msg.reply_to_message) {
        bot.sendMessage(chatId, 'សូម Reply ទៅកាន់សារបញ្ជាទិញចាស់ណាមួយ រួចវាយ /addprintbutton ម្តងទៀត។');
        return;
    }

    const oldMessage = msg.reply_to_message;

    // ពិនិត្យមើលថាតើសារនោះជាសាររបស់ Bot ខ្លួនឯងឬអត់
    const botInfo = await bot.getMe();
    if (oldMessage.from.id !== botInfo.id) {
        bot.sendMessage(chatId, 'សារនេះមិនមែនជាសាររបស់ Bot ទេ។ សូម Reply ទៅលើសារបញ្ជាទិញដែលផ្ញើដោយ Bot។');
        return;
    }

    // ពិនិត្យមើលទម្រង់សារ
    const data = parseOrderDetails(oldMessage.text);
    if (!data) {
        bot.sendMessage(chatId, 'ទម្រង់សារដែលអ្នក Reply មិនត្រឹមត្រូវទេ។ រកមិនឃើញទិន្នន័យបញ្ជាទិញ។');
        return;
    }

    try {
        // បន្ថែមប៊ូតុងទៅសារចាស់នោះ
        await bot.editMessageReplyMarkup(getPrintButtonMarkup(), {
            chat_id: oldMessage.chat.id,
            message_id: oldMessage.message_id
        });
        console.log(`Added print button to OLD message ${oldMessage.message_id}`);
        // ផ្ញើសារបញ្ជាក់ (ហើយលុបវិញបន្ទាប់ពី 5 វិនាទី)
        const confirmMsg = await bot.sendMessage(chatId, '✅ បានបន្ថែមប៊ូតុងព្រីនដោយជោគជ័យ!');
        setTimeout(() => {
            bot.deleteMessage(chatId, msg.message_id).catch(err => {
                console.warn(`Could not delete command message: ${err.message}`);
            }); // លុប command /addprintbutton
            bot.deleteMessage(chatId, confirmMsg.message_id).catch(err => {
                console.warn(`Could not delete confirm message: ${err.message}`);
            }); // លុបសារបញ្ជាក់
        }, 5000);

    } catch (err) {
        console.error('Error adding button to old message:', err);
        bot.sendMessage(chatId, 'មានបញ្ហាក្នុងការបន្ថែមប៊ូតុង។ (សារនេះប្រហែលជាចាស់ពេក ឬ Bot មិនមានសិទ្ធិ Edit)');
    }
});

// --- 6. ឡូហ្សិកគ្រប់គ្រង Callback Query (ពេលចុចប៊ូតុង) ---

bot.on('callback_query', async (callbackQuery) => {
    const msg = callbackQuery.message;
    const data = callbackQuery.data;

    if (data === 'print_label') {
        console.log(`Print button clicked for message ${msg.message_id}`);
        // 1. ស្រង់ទិន្នន័យពីសារដែលប៊ូតុងនោះនៅជាប់
        const orderData = parseOrderDetails(msg.text);

        if (!orderData) {
            // ឆ្លើយតបទៅ User ថាមានបញ្ហា
            bot.answerCallbackQuery(callbackQuery.id, {
                text: 'Error: រកមិនឃើញទិន្នន័យក្នុងសារនេះទៀតទេ!',
                show_alert: true
            });
            return;
        }

        // 2. បំប្លែងទិន្នន័យទៅជា JSON string រួច encode សម្រាប់ដាក់ក្នុង URL
        const dataString = encodeURIComponent(JSON.stringify(orderData));

        // 3. បង្កើត URL សម្រាប់ទំព័រព្រីន
        const printUrl = `${RENDER_URL}/print?data=${dataString}`;

        // 4. ឆ្លើយតបទៅ Callback Query ដោយបើក URL នោះ
        bot.answerCallbackQuery(callbackQuery.id, {
            url: printUrl
        });
    }
});

// --- 7. ឡូហ្សិកសម្រាប់ទំព័រ Web App (ទំព័រព្រីន) ---

app.get('/print', (req, res) => {
    try {
        // 1. យកទិន្នន័យពី URL query
        const dataString = req.query.data;
        if (!dataString) {
            return res.status(400).send('<h1>Error: មិនមានទិន្នន័យ</h1>');
        }

        // 2. Decode និង Parse ទិន្នន័យ
        const data = JSON.parse(decodeURIComponent(dataString));

        // 3. បង្កើត HTML สำหรับ Label
        const html = `
            <!DOCTYPE html>
            <html lang="km">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Print Label</title>
                <style>
                    body {
                        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                        margin: 0;
                        padding: 0;
                        background-color: #f0f0f0;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                    }
                    /* កំណត់ទំហំ Label */
                    .label {
                        width: 78mm;
                        height: 50mm;
                        padding: 3mm;
                        box-sizing: border-box; /* ធានាថា padding មិនធ្វើឲ្យទំហំលើស */
                        border: 1px dashed #999;
                        background-color: #ffffff;
                        overflow: hidden;
                        font-size: 10pt;
                    }
                    .label-header {
                        font-size: 12pt;
                        font-weight: bold;
                        text-align: center;
                        border-bottom: 1px solid #000;
                        padding-bottom: 2mm;
                        margin-bottom: 2mm;
                    }
                    .label-section {
                        margin-bottom: 2mm;
                    }
                    .label-section strong {
                        display: inline-block;
                        width: 30mm; /* កំណត់ទទឹងរបស់ Label */
                    }
                    .label-footer {
                        font-weight: bold;
                        text-align: center;
                        border-top: 1px solid #000;
                        padding-top: 2mm;
                        margin-top: 2mm;
                        font-size: 11pt;
                    }
                    .print-button {
                        margin-top: 20px;
                        padding: 10px 20px;
                        font-size: 16px;
                        color: white;
                        background-color: #0088cc;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                    }

                    /* CSS សម្រាប់ពេលព្រីន */
                    @media print {
                        body {
                            background-color: #ffffff;
                        }
                        .print-button {
                            display: none; /* លាក់ប៊ូតុងពេលព្រីន */
                        }
                        .label {
                            border: none;
                            margin: 0;
                            padding: 0;
                            page-break-after: always; /* ធានាថា Label នីមួយៗនៅមួយទំព័រ */
                        }
                        @page {
                            size: 78mm 50mm; /* កំណត់ទំហំក្រដាស */
                            margin: 0;
                        }
                    }
                </style>
            </head>
            <body>
                <div class="label">
                    <div class="label-header">SHIPPING LABEL</div>
                    <div class="label-section">
                        <strong>To (Info):</strong> ${data.customerInfo || 'N/A'}
                    </div>
                    <div class="label-section">
                        <strong>Phone:</strong> ${data.customerPhone || 'N/A'}
                    </div>
                    <div class="label-section">
                        <strong>Location:</strong> ${data.location || 'N/A'}
                    </div>
                    <div class="label-section">
                        <strong>Address:</strong> ${data.addressDetails || 'N/A'}
                    </div>
                    <div class="label-section">
                        <strong>Shipping:</strong> ${data.shippingMethod || 'N/A'}
                    </div>
                    <div class="label-footer">
                        Total: $${data.grandTotal} (${data.paymentStatus})
                    </div>
                </div>

                <button class="print-button" onclick="window.print()">
                    🖨️ ព្រីន Label
                </button>
            </body>
            </html>
        `;

        res.send(html);

    } catch (err) {
        console.error('Error generating print page:', err);
        res.status(500).send('<h1>Error: មានបញ្ហាក្នុងការបង្កើតទំព័រព្រីន</h1>');
    }
});

// --- 8. ចាប់ផ្ដើម Server ---

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});



import json
import random
import re
import time

import pymysql
import telegram

from config import *  # pylint: disable=E0401,W0401,W0614


db = pymysql.connect(
    host=DB_HOST,
    user=DB_USER,
    passwd=DB_PASS,
    db=DB_DB,
    charset='utf8mb4',
)
cur = db.cursor()


class STATUS:
    NEW = 'new'
    FILLING = 'filling'
    SUBMITTED = 'submitted'
    REJECTED = 'rejected'
    BANNED = 'banned'
    APPROVED = 'approved'
    JOINED = 'joined'


class PERMISSION:
    SUPER = 'super'
    GRANT = 'grant'
    REVIEW = 'review'


class Userinfo():
    full_name = None
    username = None
    status = STATUS.NEW
    kicked = False
    admin_comment = None

    def __init__(self, user_id):
        self.user_id = user_id

        cur.execute("""SELECT `full_name`, `username`, `status`, `kicked`, `admin_comment`, `question`, `answer`
                    FROM `user` WHERE `user_id` = %s""",
                    (user_id))
        row = cur.fetchone()

        if row is None:
            self.exists = False
            self.full_name = str(user_id)
        else:
            self.exists = True
            (self.full_name,
             self.username,
             self.status,
             self.kicked,
             self.admin_comment,
             self.question,
             self.answer) = row

    def format_user_id(self):
        return '<a href="tg://user?id={0}">{0}</a>'.format(
            self.user_id,
        )

    def format_full_name(self):
        if not self.exists:
            return self.format_user_id()

        return '<a href="tg://user?id={0}">{1}</a>'.format(
            self.user_id,
            self.full_name,
        )

    def format_full(self):
        if not self.exists:
            return self.format_user_id()

        return '{0} <a href="tg://user?id={0}">{1}</a>{2}'.format(
            self.user_id,
            self.full_name,
            ' (@{})'.format(self.username) if self.username else '',
        )

    def format_full_raw(self):
        if not self.exists:
            return str(self.user_id)

        return '{0} {1}{2}'.format(
            self.user_id,
            self.full_name,
            ' (@{})'.format(self.username) if self.username else '',
        )

    def update_name(self, full_name, username):
        if not self.exists:
            cur.execute("""INSERT INTO `user` (`user_id`) VALUES (%s)""",
                        (self.user_id))
            db.commit()
            self.exists = True
        if full_name != self.full_name or username != self.username:
            cur.execute("""UPDATE `user` SET `full_name` = %s, `username` = %s WHERE `user_id` = %s""",
                        (full_name, username, self.user_id))
            db.commit()

            self.full_name = full_name
            self.username = username

    def update_status(self, status):
        cur.execute("""UPDATE `user` SET `status` = %s, `updated_at` = CURRENT_TIMESTAMP WHERE `user_id` = %s""",
                    (status, self.user_id))
        db.commit()

    def update_kicked(self, kicked):
        cur.execute("""UPDATE `user` SET `kicked` = %s, `updated_at` = CURRENT_TIMESTAMP WHERE `user_id` = %s""",
                    (kicked, self.user_id))
        db.commit()

    def update_question(self, question):
        cur.execute("""UPDATE `user` SET `question` = %s, `updated_at` = CURRENT_TIMESTAMP WHERE `user_id` = %s""",
                    (question, self.user_id))
        db.commit()

    def update_answer(self, answer):
        cur.execute("""UPDATE `user` SET `answer` = %s, `updated_at` = CURRENT_TIMESTAMP WHERE `user_id` = %s""",
                    (answer, self.user_id))
        db.commit()

    def update_admin_comment(self, admin_comment):
        cur.execute("""UPDATE `user` SET `admin_comment` = %s, `updated_at` = CURRENT_TIMESTAMP WHERE `user_id` = %s""",
                    (admin_comment, self.user_id))
        db.commit()

    def get_permissions(self):
        permissions = []

        cur.execute("""SELECT `permission` FROM `permissions` WHERE `admin_user_id` = %s""",
                    (self.user_id))
        rows = cur.fetchall()
        for row in rows:
            permissions.append(row[0])

        return permissions

    def grant(self, permission):
        try:
            cur.execute("""INSERT INTO `permissions` (`admin_user_id`, `permission`) VALUES (%s, %s)""",
                        (self.user_id, permission))
            db.commit()
        except pymysql.err.IntegrityError:
            pass

    def revoke(self, permission):
        cur.execute("""DELETE FROM `permissions` WHERE `admin_user_id` = %s AND `permission` = %s""",
                    (self.user_id, permission))
        db.commit()


class System:
    def __init__(self):
        self.bot = telegram.Bot(TG_TOKEN)

    def log(self, text):
        cur.execute("""INSERT INTO `log` (`text`) VALUES (%s)""",
                    (str(text)))
        db.commit()

    def get_requests(self):
        cur.execute("""SELECT `user_id` FROM `user` WHERE `status` = %s""",
                    (STATUS.SUBMITTED))
        return cur.fetchall()

    def main(self, data):
        update = telegram.Update.de_json(data, self.bot)

        if update.inline_query:
            self.handle_inline_query(update)
            return

        if not update.effective_chat:
            self.log(json.dumps(data))
            return

        chat_id = update.effective_chat.id

        if chat_id > 0:
            self.handle_user(update)
        elif chat_id == CENSORED_CHAT_ID:
            self.handle_censored(update)
        elif chat_id == ADMIN_CHAT_ID:
            self.handle_admin(update)
        else:
            try:
                update.effective_message.reply_text(
                    '此群未獲許可使用本機器人',
                    quote=False,
                )
            except telegram.error.Unauthorized as e:
                self.log('{} send message error: {}'.format(chat_id, e))
            try:
                update.effective_chat.leave()
            except telegram.error.Unauthorized as e:
                self.log('{} leave chat error: {}'.format(chat_id, e))

    def handle_inline_query(self, update):
        m = self.parse_cmd_comment(update.inline_query.query)
        if m:
            reviewed_user_id, comment = m
            userinfo = Userinfo(reviewed_user_id)

            update.inline_query.answer(
                results=[
                    telegram.InlineQueryResultArticle(
                        id='comment',
                        title='向{}留言'.format(userinfo.full_name),
                        description='{}，留言內容為「{}」'.format(userinfo.format_full_raw(), comment),
                        input_message_content=telegram.InputTextMessageContent(
                            message_text=update.inline_query.query,
                        )
                    )
                ]
            )
            return

        reviewed_user_id = self.parse_cmd_reanswer(update.inline_query.query)
        if reviewed_user_id:
            userinfo = Userinfo(reviewed_user_id)

            update.inline_query.answer(
                results=[
                    telegram.InlineQueryResultArticle(
                        id='reanswer',
                        title='要求{}重新作答'.format(userinfo.full_name),
                        description='{}'.format(userinfo.format_full_raw()),
                        input_message_content=telegram.InputTextMessageContent(
                            message_text=update.inline_query.query,
                        )
                    )
                ]
            )
            return

        reviewed_user_id = self.parse_cmd_approve(update.inline_query.query)
        if reviewed_user_id:
            userinfo = Userinfo(reviewed_user_id)

            update.inline_query.answer(
                results=[
                    telegram.InlineQueryResultArticle(
                        id='approve',
                        title='批准{}的申請'.format(userinfo.full_name),
                        description='{}'.format(userinfo.format_full_raw()),
                        input_message_content=telegram.InputTextMessageContent(
                            message_text=update.inline_query.query,
                        )
                    )
                ]
            )
            return

        reviewed_user_id = self.parse_cmd_reject(update.inline_query.query)
        if reviewed_user_id:
            userinfo = Userinfo(reviewed_user_id)

            update.inline_query.answer(
                results=[
                    telegram.InlineQueryResultArticle(
                        id='reject',
                        title='拒絕{}的申請'.format(userinfo.full_name),
                        description='{}'.format(userinfo.format_full_raw()),
                        input_message_content=telegram.InputTextMessageContent(
                            message_text=update.inline_query.query,
                        )
                    )
                ]
            )
            return

        if update.inline_query.query:
            update.inline_query.answer(
                results=[
                    telegram.InlineQueryResultArticle(
                        id='unknown',
                        title=update.inline_query.query,
                        input_message_content=telegram.InputTextMessageContent(
                            message_text=update.inline_query.query,
                        )
                    )
                ]
            )
            return

    def handle_user(self, update):
        text = update.message.text

        if text is None:
            return

        user_id = update.effective_user.id

        self.log('user {} {}'.format(user_id, text))

        userinfo = Userinfo(user_id)
        userinfo.update_name(update.effective_user.full_name, update.effective_user.username)

        if userinfo.status == STATUS.NEW:
            if text == '/request':
                self.user_new_request(update, userinfo)
                return

            update.message.reply_text(
                '您從未進行過任何申請，使用 /request 開始新申請'
            )
            return

        elif userinfo.status == STATUS.FILLING:
            if text == '/request':
                message = '您的入群問題為：\n{}\n-----\n'.format(userinfo.question)
                if userinfo.answer:
                    message += '您目前答案為：\n{}\n-----\n'.format(userinfo.answer)
                message += '請使用 /answer 換行後接著您所有的答案，答案請註明題號'
                update.message.reply_text(message)
                return

            if re.search(r'^/answer\s*$', text):
                update.message.reply_text(
                    '請在該指令後附加您的答案，範例：\n-----\n/answer\n1. 答案一\n2. 答案二...'
                )
                return

            m = re.search(r'^/answer\s+([\s\S]+)$', text)
            if m:
                answer = m.group(1)
                userinfo.update_answer(answer)
                update.message.reply_text(
                    '已儲存您的答案但尚未提交申請，使用 /request 確認您目前儲存的答案\n'
                    + '再次使用 /answer 覆蓋您的答案\n'
                    + '使用 /submit 提交申請，提交申請後則無法再修改答案'
                )
                return

            if text == '/submit':
                userinfo.update_status(STATUS.SUBMITTED)
                userinfo.update_admin_comment(None)
                update.message.reply_text(
                    '您的入群申請已送出，請耐心等候'
                )

                message = (
                    '收到一則來自 {} 的申請\n'
                    + '使用 /review_{} 來查看申請'
                ).format(userinfo.format_full(), userinfo.user_id)
                self.bot.send_message(
                    chat_id=ADMIN_CHAT_ID,
                    text=message,
                    parse_mode=telegram.ParseMode.HTML,
                )
                return

            update.message.reply_text(
                '您正在回答入群問題，使用 /request 查看您的問題'
            )
            return

        elif userinfo.status == STATUS.SUBMITTED:
            update.message.reply_text(
                '您的入群申請已送出，請耐心等候'
            )

        elif userinfo.status == STATUS.REJECTED:
            if text == '/request':
                self.user_new_request(update, userinfo)
            else:
                message = '您的入群申請被拒絕\n'
                if userinfo.admin_comment:
                    message += '管理員有此留言：{}\n'.format(userinfo.admin_comment)
                message += '使用 /request 再次提出申請'

                update.message.reply_text(message)

        elif userinfo.status == STATUS.BANNED:
            update.message.reply_text(
                '您已被禁止提出新申請'
            )

        elif userinfo.status == STATUS.APPROVED:
            if text == '/join':
                self.user_join_link(update)
                return

            update.message.reply_text(
                '您已通過申請，使用 /join 取得入群連結'
            )
            return

        elif userinfo.status == STATUS.JOINED:
            if text == '/join':
                if PERMISSION.REVIEW in userinfo.get_permissions():
                    self.user_join_link(update, True)
                    return

                chat_member = self.bot.get_chat_member(chat_id=CENSORED_CHAT_ID, user_id=user_id)
                if chat_member.status in chat_member.LEFT:
                    self.user_join_link(update)
                    return

                if chat_member.status in chat_member.KICKED:
                    update.message.reply_text(
                        '您已被管理員踢出群組',
                    )
                    return

            update.message.reply_text(
                '您已加入群組',
            )
            return

    def user_new_request(self, update, userinfo):
        user_questions = []
        for qid, questions in enumerate(QUESTIONS, 1):
            user_questions.append('{}. {}'.format(qid, random.choice(questions)))
        user_questions = '\n'.join(user_questions)

        userinfo.update_status(STATUS.FILLING)
        userinfo.update_question(user_questions)
        userinfo.update_answer(None)

        update.message.reply_text(
            '您的入群問題為：\n{}\n----\n請使用 /answer 換行後接著您的答案，答案請註明題號'.format(user_questions)
        )

    def user_join_link(self, update, isadmin=False):
        link = self.bot.export_chat_invite_link(chat_id=CENSORED_CHAT_ID)
        message = (
            '加群連結為\n'
            + '{}\n'
        ).format(link)
        if not isadmin:
            message += (
                '請立即加入群組以免連結失效\n'
                + '此連結僅限您可使用，分享給他人將導致您的入群許可被撤銷\n'
            )

        update.message.reply_text(
            message,
            disable_web_page_preview=True,
        )

    def handle_censored(self, update):
        if update.message and update.message.new_chat_members:
            new_member = update.effective_message.new_chat_members[0]
            user_id = new_member.id

            userinfo = Userinfo(user_id)
            userinfo.update_name(new_member.full_name, new_member.username)

            if userinfo.status == STATUS.APPROVED:
                userinfo.update_status(STATUS.JOINED)
                update.message.reply_text(
                    '{} 已通過申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            elif userinfo.status == STATUS.JOINED:
                update.message.reply_text(
                    '{} 已通過申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            else:
                update.message.reply_text(
                    '{} 未通過申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )

                until_date = int(time.time() + BAN_DURATION)
                update.effective_chat.kick_member(
                    user_id=user_id,
                    until_date=until_date,
                )
                userinfo.update_kicked(True)

    def handle_admin(self, update):
        text = update.message.text

        if text is None:
            return

        admininfo = Userinfo(update.effective_user.id)
        admininfo.update_name(update.effective_user.full_name, update.effective_user.username)

        self.log('admin {}'.format(text))

        m = re.search(r'^/review(?:@{0})?[ _]+(\d+)(?:@{0})?$'.format(self.bot.username), text)
        if m:
            reviewed_user_id = int(m.group(1))
            userinfo = Userinfo(reviewed_user_id)

            if userinfo.status == STATUS.SUBMITTED:
                message = (
                    '{0} 的申請問題如下：\n'
                    + '{1}\n'
                    + '-----\n'
                    + '答案如下：\n'
                    + '{2}'
                ).format(
                    userinfo.format_full(),
                    userinfo.question,
                    userinfo.answer,
                )
                update.message.reply_text(
                    text=message,
                    parse_mode=telegram.ParseMode.HTML,
                    reply_markup=telegram.InlineKeyboardMarkup([
                        [
                            telegram.InlineKeyboardButton(text='留言', switch_inline_query_current_chat='/comment {} 內容'.format(reviewed_user_id)),
                            telegram.InlineKeyboardButton(text='重答', switch_inline_query_current_chat='/reanswer {}'.format(reviewed_user_id)),
                            telegram.InlineKeyboardButton(text='批准', switch_inline_query_current_chat='/approve {}'.format(reviewed_user_id)),
                            telegram.InlineKeyboardButton(text='拒絕', switch_inline_query_current_chat='/reject {}'.format(reviewed_user_id)),
                        ]
                    ])
                )
            else:
                update.message.reply_text(
                    '{} 目前沒有申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

        m = self.parse_cmd_comment(text)
        if m:
            if PERMISSION.REVIEW not in admininfo.get_permissions():
                update.message.reply_text(
                    '您沒有足夠權限進行此操作',
                )
                return

            reviewed_user_id, comment = m

            userinfo = Userinfo(reviewed_user_id)

            if userinfo.status == STATUS.SUBMITTED:
                userinfo.update_admin_comment(comment)
                update.message.reply_text('已設定回應訊息，會在要求重答、批准或拒絕時同時送出')
            else:
                update.message.reply_text(
                    '{} 目前沒有申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

        reviewed_user_id = self.parse_cmd_reanswer(text)
        if reviewed_user_id:
            if PERMISSION.REVIEW not in admininfo.get_permissions():
                update.message.reply_text(
                    '您沒有足夠權限進行此操作',
                )
                return

            userinfo = Userinfo(reviewed_user_id)

            if userinfo.status == STATUS.SUBMITTED:
                userinfo.update_status(STATUS.FILLING)
                update.message.reply_text(
                    '已要求 {} 重新作答，剩餘{}筆申請'.format(
                        userinfo.format_full(),
                        len(self.get_requests()),
                    ),
                    parse_mode=telegram.ParseMode.HTML,
                )

                message = '管理員要求您重新作答'
                if userinfo.admin_comment:
                    message += '\n管理員有此留言：{}\n'.format(userinfo.admin_comment)
                message += '使用 /request 查看您的問題及之前的答案，使用 /answer 修改答案'

                self.bot.send_message(
                    chat_id=reviewed_user_id,
                    text=message,
                )
            else:
                update.message.reply_text(
                    '{} 目前沒有申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

        reviewed_user_id = self.parse_cmd_approve(text)
        if reviewed_user_id:
            if PERMISSION.REVIEW not in admininfo.get_permissions():
                update.message.reply_text(
                    '您沒有足夠權限進行此操作',
                )
                return

            userinfo = Userinfo(reviewed_user_id)

            if userinfo.status == STATUS.SUBMITTED:
                userinfo.update_status(STATUS.APPROVED)
                update.message.reply_text(
                    '已批准 {} 的申請，剩餘{}筆申請'.format(
                        userinfo.format_full(),
                        len(self.get_requests()),
                    ),
                    parse_mode=telegram.ParseMode.HTML,
                )

                chat_member = self.bot.get_chat_member(chat_id=CENSORED_CHAT_ID, user_id=reviewed_user_id)
                if userinfo.kicked and chat_member.status not in [chat_member.ADMINISTRATOR, chat_member.CREATOR]:
                    try:
                        self.bot.unban_chat_member(chat_id=CENSORED_CHAT_ID, user_id=reviewed_user_id)
                        userinfo.update_kicked(False)
                    except telegram.error.BadRequest as e:
                        update.message.reply_text(
                            '解封時發生錯誤：{}'.format(e),
                        )

                message = '您的入群申請已通過'
                if userinfo.admin_comment:
                    message += '\n管理員有此留言：{}\n'.format(userinfo.admin_comment)
                message += '\n稍待幾分鐘後使用 /join 取得加群連結（如立即加入可能遭誤判為未通過申請）'

                self.bot.send_message(
                    chat_id=reviewed_user_id,
                    text=message,
                )
            else:
                update.message.reply_text(
                    '{} 目前沒有申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

        reviewed_user_id = self.parse_cmd_reject(text)
        if reviewed_user_id:
            if PERMISSION.REVIEW not in admininfo.get_permissions():
                update.message.reply_text(
                    '您沒有足夠權限進行此操作',
                )
                return

            userinfo = Userinfo(reviewed_user_id)

            if userinfo.status == STATUS.SUBMITTED:
                userinfo.update_status(STATUS.REJECTED)
                update.message.reply_text(
                    '已拒絕 {} 的申請，剩餘{}筆申請'.format(
                        userinfo.format_full(),
                        len(self.get_requests()),
                    ),
                    parse_mode=telegram.ParseMode.HTML,
                )

                message = '您的入群申請被拒絕\n'
                if userinfo.admin_comment:
                    message += '管理員有此留言：{}\n'.format(userinfo.admin_comment)
                message += '使用 /request 再次提出申請'

                self.bot.send_message(
                    chat_id=reviewed_user_id,
                    text=message,
                )
            else:
                update.message.reply_text(
                    '{} 目前沒有申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

        m = re.search(r'^/ban (\d+)$', text)
        if m:
            reviewed_user_id = int(m.group(1))
            userinfo = Userinfo(reviewed_user_id)

            if userinfo.exists:
                userinfo.update_status(STATUS.BANNED)
                update.message.reply_text(
                    '已禁止 {} 的申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            else:
                update.message.reply_text(
                    '{} 從未申請過，無法封鎖'.format(userinfo.format_user_id()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

        if re.search(r'^/list_?request$', text):
            requests = self.get_requests()
            if len(requests) == 0:
                message = '目前沒有申請'
            else:
                message = '目前有{}筆申請：\n'.format(len(requests))
                for request in requests:
                    userinfo = Userinfo(request[0])
                    message += '{}\n'.format(userinfo.format_full())
                message += '使用 /review 來查看申請'
            update.message.reply_text(
                message,
                parse_mode=telegram.ParseMode.HTML,
            )
            return

        m = re.search(r'^/(grant|revoke)[_ ](grant|review)$', text)
        if m:
            action = m.group(1)
            permission = m.group(2)
            required_permissions = {
                'grant': PERMISSION.SUPER,
                'review': PERMISSION.GRANT,
            }
            given_permission = {
                'grant': PERMISSION.GRANT,
                'review': PERMISSION.REVIEW,
            }

            if required_permissions[permission] not in admininfo.get_permissions():
                update.message.reply_text(
                    '您沒有足夠權限進行此操作',
                )
                return

            if update.message.reply_to_message:
                reply_to_message = update.message.reply_to_message
                target_user_id = reply_to_message.from_user.id

                userinfo = Userinfo(target_user_id)

                userinfo.update_name(reply_to_message.from_user.full_name, reply_to_message.from_user.username)

                if action == 'grant':
                    userinfo.grant(given_permission[permission])
                    update.message.reply_text(
                        '已成功授予 {} {} 權限'.format(
                            userinfo.format_full(),
                            given_permission[permission],
                        ),
                        parse_mode=telegram.ParseMode.HTML,
                    )
                elif action == 'revoke':
                    userinfo.revoke(given_permission[permission])
                    update.message.reply_text(
                        '已成功除去 {} {} 權限'.format(
                            userinfo.format_full(),
                            given_permission[permission],
                        ),
                        parse_mode=telegram.ParseMode.HTML,
                    )
                else:
                    self.log('unknown action')
            else:
                update.message.reply_text(
                    '需回應訊息以授權/除權',
                )
            return

        if re.search(r'^/list_?permissions?$', text):
            cur.execute("""SELECT `admin_user_id`, `permission` FROM `permissions` ORDER BY `admin_user_id` ASC""")
            rows = cur.fetchall()
            users = {
                'review': [],
                'grant': [],
                'super': [],
            }
            for row in rows:
                userinfo = Userinfo(row[0])
                users[row[1]].append(userinfo.format_full_name())
            message = '權限表：\n'
            for permission in ['review', 'grant', 'super']:
                message += '{}：{}\n'.format(permission, '、'.join(users[permission]))
            update.message.reply_text(
                message,
                parse_mode=telegram.ParseMode.HTML,
            )
            return

        # Debug mode on

        m = re.search(r'/set_status (\d+) (new|filling|submitted|rejected|banned|approved|joined)$', text)
        if m and DEBUG_MODE:
            if PERMISSION.REVIEW not in admininfo.get_permissions():
                update.message.reply_text(
                    '您沒有足夠權限進行此操作',
                )
                return

            reviewed_user_id = int(m.group(1))
            userinfo = Userinfo(reviewed_user_id)
            status = m.group(2)

            if userinfo.exists:
                userinfo.update_status(status)
                update.message.reply_text(
                    '已將 {} 的狀態改為 {}'.format(userinfo.format_full(), status),
                    parse_mode=telegram.ParseMode.HTML,
                )
            else:
                update.message.reply_text(
                    '{} 從未申請過，無法執行'.format(userinfo.format_user_id()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

        m = re.search(r'/delete (\d+)$', text)
        if m and DEBUG_MODE:
            if PERMISSION.REVIEW not in admininfo.get_permissions():
                update.message.reply_text(
                    '您沒有足夠權限進行此操作',
                )
                return

            reviewed_user_id = int(m.group(1))
            userinfo = Userinfo(reviewed_user_id)

            if userinfo.exists:
                cur.execute("""DELETE FROM `user` WHERE `user_id` = %s""",
                            (reviewed_user_id))
                db.commit()
                update.message.reply_text(
                    '已刪除 {} 的申請'.format(userinfo.format_full()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            else:
                update.message.reply_text(
                    '{} 從未申請過，無法執行'.format(userinfo.format_user_id()),
                    parse_mode=telegram.ParseMode.HTML,
                )
            return

    def parse_cmd_comment(self, text):
        m = re.search(r'^/comment\s*(\d+)\s*([\s\S]*)$', text)
        if m:
            return int(m.group(1)), m.group(2)
        return None

    def parse_cmd_reanswer(self, text):
        m = re.search(r'^/reanswer[ _]+(\d+)$', text)
        if m:
            return int(m.group(1))
        return None

    def parse_cmd_approve(self, text):
        m = re.search(r'^/approve[ _]+(\d+)$', text)
        if m:
            return int(m.group(1))
        return None

    def parse_cmd_reject(self, text):
        m = re.search(r'^/reject[ _]+(\d+)$', text)
        if m:
            return int(m.group(1))
        return None


if __name__ == "__main__":
    system = System()
    system.log('test')

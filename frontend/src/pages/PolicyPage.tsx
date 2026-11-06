import React from 'react'
import { Link } from 'react-router-dom'

export default function PolicyPage() {
  return (
    <div style={{ marginTop: 16, maxWidth: 640 }}>
      <h1 className="section-title" style={{ marginTop: 0 }}>Правила и гарантии</h1>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3>Доставка</h3>
        <p className="hint">
          Районы: Худжанд, Гафуров, Хистеварз, Овчикалача, Сартукай, Унчи, Бустон и др.
          Сумму доставки уточняет менеджер после оплаты товара. Также можно забрать заказ в магазине.
        </p>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3>Самовывоз и срок хранения</h3>
        <ul className="hint" style={{ paddingLeft: 18, margin: 0 }}>
          <li>Можно забрать заказ в магазине после подтверждения оплаты.</li>
          <li><strong>Срок хранения в магазине — 3 дня</strong> с момента, когда заказ готов к выдаче.</li>
          <li>Если за 3 дня товар не забрали: оплата возвращается клиенту, товар снова появляется в каталоге.</li>
          <li>Пока заказ в магазине, можно нажать «Заказать доставку» — менеджер укажет цену, вы подтвердите.</li>
        </ul>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3>Оплата</h3>
        <p className="hint">
          DC (Душанбе Сити), Эсхата (карта), Алиф. После перевода загрузите скрин чека —
          проверка обычно в течение нескольких часов. Также можно оплатить заказ <strong>баллами</strong>
          (1 балл = 1 TJS), если баллов достаточно.
        </p>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3>Промокоды</h3>
        <ul className="hint" style={{ paddingLeft: 18, margin: 0 }}>
          <li>На шаге оплаты (выбор способа оплаты) есть поле «Промокод».</li>
          <li>Введите код и нажмите «Применить». Если код верный — скидка активируется сразу.</li>
          <li>Скидка может быть в процентах (например 10%) или фиксированной суммой в сомони (например −20 TJS) — как указано на промокоде.</li>
          <li>Промокод необязателен: без него заказ оформляется по обычной цене товара.</li>
        </ul>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3>Система баллов</h3>
        <ul className="hint" style={{ paddingLeft: 18, margin: 0 }}>
          <li>Баллы можно использовать как настоящие деньги: 1 балл = 1 сомони (TJS).</li>
          <li>Если у вас достаточно баллов и сумма заказа (после скидок) не больше баланса — можно оплатить заказ только баллами, без перевода.</li>
          <li>Баллы начисляются <strong>только с рефералов</strong>: за свои покупки баллы не даются.</li>
          <li><strong>+1 балл</strong> вам, когда ваш реферал (друг по вашему коду) совершает покупку на сумму <strong>выше 250 сомони</strong> (после подтверждения оплаты).</li>
          <li>Баланс баллов смотрите в разделе «Профиль».</li>
        </ul>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3>Как подключить Telegram к приложению</h3>
        <p className="hint" style={{ marginBottom: 10 }}>
          Уведомления о статусе заказа и оплате приходят в Telegram после привязки аккаунта.
        </p>
        <ol className="hint" style={{ paddingLeft: 18, margin: 0 }}>
          <li>
            Откройте бота{' '}
            <a href="https://t.me/velorashoping_bot" target="_blank" rel="noreferrer">
              @velorashoping_bot
            </a>{' '}
            в Telegram и нажмите <strong>Start</strong> (или напишите <code>/start</code>).
          </li>
          <li>
            <strong>Как узнать свой Telegram ID (Chat ID):</strong>
            <ul style={{ paddingLeft: 18, marginTop: 6 }}>
              <li>
                Самый простой способ: напишите боту VELORA <code>/start</code> — если аккаунт ещё не привязан,
                бот покажет ваш <strong>Chat ID</strong> в сообщении (число вида <code>123456789</code>).
              </li>
              <li>
                Либо откройте бота{' '}
                <a href="https://t.me/userinfobot" target="_blank" rel="noreferrer">
                  @userinfobot
                </a>
                , нажмите Start — он пришлёт ваш Id.
              </li>
              <li>
                Либо{' '}
                <a href="https://t.me/getmyid_bot" target="_blank" rel="noreferrer">
                  @getmyid_bot
                </a>
                — то же самое.
              </li>
            </ul>
          </li>
          <li>
            В приложении VELORA откройте <strong>Профиль</strong> → блок «Telegram-уведомления».
          </li>
          <li>
            Вставьте Chat ID в поле и нажмите <strong>Сохранить</strong>.
          </li>
          <li>
            Бот подтвердит привязку. После этого статусы заказов и подтверждение оплаты будут приходить в Telegram.
          </li>
        </ol>
        <p className="hint" style={{ marginTop: 10 }}>
          Если бот пишет, что аккаунт не привязан — скопируйте показанный Chat ID и сохраните его в Профиле ещё раз.
        </p>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3>Возврат</h3>
        <ul className="hint" style={{ paddingLeft: 18, margin: 0 }}>
          <li>Если товар не соответствует описанию — возврат возможен в течение 3 дней после получения.</li>
          <li>Товар должен быть в исходном виде, с бирками.</li>
          <li>Брак по вине поставщика — замена или возврат оплаты.</li>
          <li>Отказ от доставки после выставления суммы — возврат оплаты товара (минус комиссия банка, если была).</li>
        </ul>
      </div>

      <Link to="/" className="btn-accent" style={{ display: 'inline-block', width: 'auto', padding: '10px 18px' }}>На главную</Link>
    </div>
  )
}

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError, api } from "../api/client";
import type { ChatMessage, ChatSummary } from "../api/types";
import { Text } from "../ui/primitives";
import { Reveal } from "../ui/Reveal";
import { dateTime } from "../lib/format";
import ChatPanel from "../chat/ChatPanel";

const SECONDARY = "var(--color-light-text-secondary)";
const POLL_MS = 5000;

/**
 * Вопросы клиентов в рабочем месте сотрудника.
 *
 * Слева список диалогов: сверху те, где клиент ждёт ответа. Справа сама
 * переписка. Это та же переписка, что клиент видит у себя в кабинете —
 * просто с другой стороны.
 */
export default function Chats() {
  const [list, setList] = useState<ChatSummary[] | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    try {
      const chats = await api.backoffice.chats();
      setList(chats);
      // первый диалог открываем сразу: пустой экран справа ничего не объясняет
      setActive((current) => current ?? chats[0]?.inn ?? null);
    } catch (e) {
      setError((e as ApiError).message);
    }
  }, []);

  const loadThread = useCallback(async () => {
    if (active === null) return;
    try {
      setMessages((await api.backoffice.chat(active)).messages);
    } catch (e) {
      setError((e as ApiError).message);
    }
  }, [active]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  useEffect(() => {
    setMessages([]);
    void loadThread();
  }, [loadThread]);

  // новые вопросы и ответы подтягиваются сами
  useEffect(() => {
    const timer = setInterval(() => {
      void loadList();
      void loadThread();
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [loadList, loadThread]);

  async function reply(text: string) {
    if (active === null) return;
    setBusy(true);
    setError(null);
    try {
      setMessages((await api.backoffice.reply(active, text)).messages);
      void loadList();
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  const current = list?.find((c) => c.inn === active) ?? null;

  return (
    <>
      <Link to="/underwriter" className="cb-back">
        ← Очередь заявок
      </Link>

      <Reveal>
        <div className="cb-head">
          <div>
            <Text view="promo-h2" tag="h1">
              Вопросы клиентов
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              Та же переписка, что клиент видит в своём кабинете. Сверху — те, кто ждёт ответа.
            </Text>
          </div>
        </div>
      </Reveal>

      {list !== null && list.length === 0 && (
        <Reveal>
          <section className="cb-card">
            <Text view="accent-primary-large" tag="h2">
              Вопросов пока нет
            </Text>
            <Text view="primary-small" color={SECONDARY} style={{ marginTop: 8 }}>
              Как только клиент напишет из кабинета, диалог появится здесь.
            </Text>
          </section>
        </Reveal>
      )}

      {list !== null && list.length > 0 && (
        <div className="ch-workspace">
          <div className="ch-threads">
            {list.map((c) => (
              <button
                key={c.inn}
                type="button"
                className="ch-thread"
                aria-pressed={c.inn === active}
                onClick={() => setActive(c.inn)}
              >
                <div className="ch-thread-head">
                  <span className="ch-thread-name">{c.company_name}</span>
                  {c.unread > 0 && <span className="ch-badge">{c.unread}</span>}
                </div>
                <div className="ch-thread-last">
                  {c.last_author === "support" && "Вы: "}
                  {c.last_text}
                </div>
                <div className="ch-thread-time">
                  ИНН {c.inn} · {dateTime(c.last_at)}
                </div>
              </button>
            ))}
          </div>

          <section className="cb-card-white cb-chat-wide">
            <Text view="accent-primary-large" tag="h2">
              {current?.company_name ?? "Переписка"}
            </Text>
            {current && (
              <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 4 }}>
                ИНН {current.inn}
              </Text>
            )}

            <ChatPanel
              side="support"
              messages={messages}
              busy={busy}
              error={error}
              placeholder="Ответ клиенту"
              emptyText="В этом диалоге пока нет сообщений."
              onSend={reply}
            />
          </section>
        </div>
      )}
    </>
  );
}

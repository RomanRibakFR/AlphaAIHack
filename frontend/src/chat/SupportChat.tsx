import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { ChatMessage } from "../api/types";
import { Text } from "../ui/primitives";
import ChatPanel from "./ChatPanel";

const SECONDARY = "var(--color-light-text-secondary)";
const POLL_MS = 5000;

/**
 * Чат клиента с поддержкой в кабинете.
 *
 * Переписка общая на компанию, а не на заявку: чаще всего вопрос возникает
 * до подачи или не про конкретную заявку вовсе.
 */
export default function SupportChat({ inn }: { inn: string }) {
  const [messages, setMessages] = useState<ChatMessage[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const thread = await api.chat.thread(inn);
      setMessages(thread.messages);
      setError(null);
    } catch (e) {
      setError((e as ApiError).message);
    }
  }, [inn]);

  useEffect(() => {
    void load();
  }, [load]);

  // ответ поддержки приходит сам, без перезагрузки страницы
  useEffect(() => {
    const timer = setInterval(() => void load(), POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  async function send(text: string) {
    setBusy(true);
    setError(null);
    try {
      setMessages((await api.chat.send(inn, text)).messages);
    } catch (e) {
      setError((e as ApiError).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="cb-card-white cb-chat">
      <Text view="accent-primary-large" tag="h2">
        Поддержка
      </Text>
      <Text view="secondary-medium" color={SECONDARY} style={{ marginTop: 4 }}>
        Отвечает кредитный специалист банка
      </Text>

      <ChatPanel
        side="client"
        messages={messages ?? []}
        busy={busy}
        error={error}
        placeholder="Спросите о заявке, условиях или документах"
        emptyText="Задайте вопрос — ответим здесь же, звонить и писать на почту не нужно."
        onSend={send}
      />
    </section>
  );
}

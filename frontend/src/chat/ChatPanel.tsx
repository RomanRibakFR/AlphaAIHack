import { useEffect, useRef, useState } from "react";
import { Button } from "@alfalab/core-components/button";
import { Textarea } from "@alfalab/core-components/textarea";
import type { ChatAuthor, ChatMessage } from "../api/types";
import { Text } from "../ui/primitives";
import { dateTime } from "../lib/format";
import "./chat.css";

const SECONDARY = "var(--color-light-text-secondary)";

/**
 * Переписка с поддержкой — одна и та же в кабинете клиента и в рабочем месте
 * сотрудника. Отличает только `side`: чьи сообщения показывать своими.
 *
 * Компонент ничего не загружает сам — ему передают сообщения и обработчик
 * отправки. Так один и тот же вид работает с двумя разными ручками API.
 */
export default function ChatPanel({
  side,
  messages,
  busy,
  error,
  placeholder,
  emptyText,
  onSend,
}: {
  side: ChatAuthor;
  messages: ChatMessage[];
  busy: boolean;
  error: string | null;
  placeholder: string;
  emptyText: string;
  onSend: (text: string) => void;
}) {
  const [text, setText] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const count = messages.length;

  // новое сообщение — прокручиваем к нему, иначе ответ уедет за край
  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTop = list.scrollHeight;
  }, [count]);

  function submit() {
    const value = text.trim();
    if (value === "" || busy) return;
    onSend(value);
    setText("");
  }

  return (
    <div className="ch-panel">
      <div className="ch-list" ref={listRef}>
        {messages.length === 0 ? (
          <Text view="secondary-medium" color={SECONDARY} className="ch-empty">
            {emptyText}
          </Text>
        ) : (
          messages.map((m) => (
            <div key={m.id} className="ch-msg" data-mine={m.author === side}>
              <div className="ch-bubble">{m.text}</div>
              <div className="ch-time">
                {m.author === side ? "вы" : m.author === "support" ? "поддержка" : "клиент"} ·{" "}
                {dateTime(m.created_at)}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="ch-form">
        <Textarea
          placeholder={placeholder}
          block
          maxRows={4}
          value={text}
          onChange={(_, { value }) => setText(value)}
          onKeyDown={(e) => {
            // Enter отправляет, Shift+Enter переносит строку — как в мессенджерах
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <Button
          view="accent"
          size={40}
          block
          className="mo-press"
          loading={busy}
          disabled={text.trim() === ""}
          onClick={submit}
        >
          Отправить
        </Button>
      </div>

      {error && (
        <Text view="secondary-medium" color="var(--color-light-text-negative)">
          {error}
        </Text>
      )}
    </div>
  );
}

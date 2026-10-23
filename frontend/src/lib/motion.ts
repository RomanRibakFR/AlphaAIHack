/** Движок анимаций лендинга.
 *
 *  Словарь эффектов взят с 60fps.design (reveal, stagger, ticker, grow,
 *  spring, draw, shimmer, morph). Снипперы там на SwiftUI, поэтому для веба
 *  всё написано здесь заново на IntersectionObserver и requestAnimationFrame.
 *
 *  Правило одно: при prefers-reduced-motion движение выключается полностью,
 *  а не ускоряется. Анимация — украшение, контент должен читаться без неё.
 */
import { useEffect, useRef, useState } from "react";

export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/* ——— общий наблюдатель появления ———
 *
 * Почему не IntersectionObserver: он сообщает только о пересечении порога.
 * Если страницу листнули рывком — якорь, Ctrl+End, восстановленная позиция
 * после перезагрузки, — секция успевает проскочить мимо окна между замерами.
 * События не будет, и блок навсегда останется с opacity: 0, то есть контент
 * просто пропадёт. Поэтому считаем положение сами: один слушатель прокрутки
 * на страницу, замеры сложены в один кадр.
 */

type Watcher = { el: HTMLElement; offset: number; reveal: () => void };

const watchers = new Set<Watcher>();
let frame = 0;
let listening = false;

function check() {
  frame = 0;
  const height = window.innerHeight;

  for (const watcher of [...watchers]) {
    const { top } = watcher.el.getBoundingClientRect();
    // верх элемента поднялся выше нижней кромки окна: либо он виден,
    // либо уже уехал вверх (top отрицательный) — показываем в обоих случаях
    if (top < height - watcher.offset) {
      watchers.delete(watcher);
      watcher.reveal();
    }
  }

  if (watchers.size === 0) stopListening();
}

function schedule() {
  if (frame === 0) frame = requestAnimationFrame(check);
}

function startListening() {
  if (listening) return;
  listening = true;
  window.addEventListener("scroll", schedule, { passive: true });
  window.addEventListener("resize", schedule, { passive: true });
}

function stopListening() {
  if (!listening) return;
  listening = false;
  window.removeEventListener("scroll", schedule);
  window.removeEventListener("resize", schedule);
}

/**
 * Элемент добрался до окна хотя бы раз.
 *
 * Обратно в false не переключается: секция, которую уже показали,
 * не должна гаснуть при обратной прокрутке.
 */
export function useInView<T extends HTMLElement>(options?: {
  /** на сколько раньше нижней кромки окна показывать, px */
  offset?: number;
}) {
  const { offset = 60 } = options ?? {};
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    if (prefersReducedMotion()) {
      setInView(true);
      return;
    }

    const watcher: Watcher = { el: node, offset, reveal: () => setInView(true) };
    watchers.add(watcher);
    startListening();
    schedule(); // при монтировании элемент может быть уже на экране

    return () => {
      watchers.delete(watcher);
      if (watchers.size === 0) stopListening();
    };
  }, [offset]);

  return { ref, inView };
}

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

/**
 * Ticker: число не перескакивает, а добегает до цели.
 *
 * Используется в калькуляторе (платёж меняется вслед за слайдером)
 * и в показателях геро-блока.
 */
export function useCountUp(target: number, options?: { duration?: number; enabled?: boolean }) {
  const { duration = 450, enabled = true } = options ?? {};
  const [value, setValue] = useState(enabled ? 0 : target);
  const fromRef = useRef(0);
  const frameRef = useRef(0);

  useEffect(() => {
    if (!enabled || prefersReducedMotion()) {
      setValue(target);
      return;
    }

    const from = fromRef.current;
    const delta = target - from;
    if (delta === 0) return;

    const start = performance.now();

    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const current = from + delta * easeOutCubic(progress);
      fromRef.current = current;
      setValue(current);
      if (progress < 1) frameRef.current = requestAnimationFrame(tick);
      else fromRef.current = target;
    };

    frameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameRef.current);
  }, [target, duration, enabled]);

  return value;
}

/**
 * Прогресс прокрутки страницы, 0—1. Для полоски под шапкой.
 */
export function useScrollProgress(): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const onScroll = () => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(scrollable > 0 ? window.scrollY / scrollable : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return progress;
}

/**
 * Шапка становится плотной, когда страницу прокрутили от самого верха.
 */
export function useScrolled(offset = 8): boolean {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > offset);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [offset]);

  return scrolled;
}

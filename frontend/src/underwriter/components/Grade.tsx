import { Text } from "../../ui/primitives";

/**
 * Класс риска и вероятность дефолта.
 *
 * Два числа рядом не случайно: класс — это ответ модели одним словом,
 * PD — само число, по которому класс присвоен. Специалисту нужно и то
 * и другое, иначе непонятно, насколько заявка близка к границе класса.
 */
export default function Grade({ grade, pd }: { grade: string | null; pd: string | null }) {
  if (!grade && !pd) {
    return (
      <Text view="secondary-medium" color="var(--color-light-text-secondary)">
        оценки нет
      </Text>
    );
  }

  return (
    <span className="uw-grade" data-grade={grade ?? "none"}>
      <b>{grade ?? "—"}</b>
      {pd && <span>PD {(Number(pd) * 100).toLocaleString("ru-RU", { maximumFractionDigits: 2 })}%</span>}
    </span>
  );
}

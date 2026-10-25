import { useState } from "react";
import type { ReactElement } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import ApplicationCard from "./cabinet/ApplicationCard";
import CabinetLayout from "./cabinet/CabinetLayout";
import Dashboard from "./cabinet/Dashboard";
import NewApplication from "./cabinet/NewApplication";
import StatePreview from "./screens/StatePreview";
import ApplicationReview from "./underwriter/ApplicationReview";
import Chats from "./underwriter/Chats";
import Queue from "./underwriter/Queue";
import UnderwriterLayout from "./underwriter/UnderwriterLayout";
import UiKit from "./screens/UiKit";
import AuthModal from "./landing/AuthModal";
import NotFound from "./landing/NotFound";
import Landing from "./landing/Landing";
import { currentInn, signIn, signOut } from "./lib/session";

/** Топбар прототипа кабинета. Временный: кабинет ещё не переведён на дизайн-систему. */
function Topbar({ inn, onSignOut }: { inn: string | null; onSignOut: () => void }) {
  return (
    <header className="topbar">
      <b>Кредитный кабинет</b>
      <nav>
        <Link to="/">На сайт</Link>
        <Link to="/cabinet">Кабинет</Link>
        <Link to="/new">Новая заявка</Link>
        <Link to="/underwriter">Сотрудник банка</Link>
        <Link to="/preview">Все состояния</Link>
        <Link to="/ui-kit">Дизайн-система</Link>
      </nav>
      <span className="who">
        {inn ? (
          <>
            ИНН {inn} <button onClick={onSignOut}>выйти</button>
          </>
        ) : (
          <Link to="/login">войти</Link>
        )}
      </span>
    </header>
  );
}

export default function App() {
  // ИНН вместо авторизации, см. lib/session.ts
  const [inn, setInn] = useState<string | null>(currentInn());
  const navigate = useNavigate();

  function handleSignIn(value: string) {
    signIn(value);
    setInn(value);
    navigate("/cabinet");
  }

  function handleSignOut() {
    signOut();
    setInn(null);
    navigate("/");
  }

  /** Экраны клиента без ИНН не имеют смысла — отправляем на вход. */
  const guard = (build: (inn: string) => ReactElement) =>
    inn === null ? <Navigate to="/login" replace /> : build(inn);

  /* Вход — окно поверх лендинга, но со своим адресом:
     ссылку на /login можно дать напрямую, закрытие возвращает на главную. */
  const landingWith = (modal: ReactElement | null) => (
    <>
      <Landing />
      {modal}
    </>
  );

  /** Экран кабинета в его оболочке: тёмная шапка, светлое полотно. */
  const inCabinet = (screen: ReactElement) =>
    inn === null ? (
      <Navigate to="/login" replace />
    ) : (
      <CabinetLayout inn={inn} onSignOut={handleSignOut}>
        {screen}
      </CabinetLayout>
    );

  /** Рабочее место сотрудника: своя оболочка, вход по /staff. */
  const inBackoffice = (screen: ReactElement) => <UnderwriterLayout>{screen}</UnderwriterLayout>;

  /** Служебные экраны прототипа пока живут в старой обёртке. */
  const inProto = (screen: ReactElement) => (
    <div className="layout">
      <Topbar inn={inn} onSignOut={handleSignOut} />
      {screen}
    </div>
  );

  return (
    <Routes>
      <Route path="/" element={landingWith(null)} />
      <Route
        path="/login"
        element={landingWith(<AuthModal mode="client" onSignIn={handleSignIn} />)}
      />
      <Route
        path="/staff"
        element={landingWith(<AuthModal mode="staff" onSignIn={handleSignIn} />)}
      />

      {/* Разделы, которых в прототипе нет */}
      <Route path="/private" element={<NotFound />} />
      <Route path="/corporate" element={<NotFound />} />

      <Route path="/cabinet" element={inCabinet(guard((i) => <Dashboard inn={i} />))} />
      <Route path="/new" element={inCabinet(guard((i) => <NewApplication inn={i} />))} />
      <Route path="/application/:id" element={inCabinet(<ApplicationCard />)} />
      <Route path="/underwriter" element={inBackoffice(<Queue />)} />
      <Route path="/underwriter/chats" element={inBackoffice(<Chats />)} />
      <Route path="/underwriter/:id" element={inBackoffice(<ApplicationReview />)} />
      <Route path="/preview" element={inProto(<StatePreview />)} />
      <Route path="/ui-kit" element={<UiKit />} />

      {/* Любой незнакомый адрес — туда же */}
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

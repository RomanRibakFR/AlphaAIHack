import { useState } from "react";
import type { ReactElement } from "react";
import { Link, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import ApplicationCard from "./screens/ApplicationCard";
import Dashboard from "./screens/Dashboard";
import NewApplication from "./screens/NewApplication";
import StatePreview from "./screens/StatePreview";
import Underwriter from "./screens/Underwriter";
import UiKit from "./screens/UiKit";
import AuthModal from "./landing/AuthModal";
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

  const cabinet = (
    <div className="layout">
      <Topbar inn={inn} onSignOut={handleSignOut} />

      <Routes>
        <Route path="/cabinet" element={guard((i) => <Dashboard inn={i} />)} />
        <Route path="/new" element={guard((i) => <NewApplication inn={i} />)} />
        <Route path="/application/:id" element={guard(() => <ApplicationCard />)} />
        <Route path="/underwriter" element={<Underwriter />} />
        <Route path="/preview" element={<StatePreview />} />
        <Route path="*" element={<p>Такой страницы нет.</p>} />
      </Routes>
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
      <Route path="/ui-kit" element={<UiKit />} />
      <Route path="*" element={cabinet} />
    </Routes>
  );
}

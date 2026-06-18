"use client";

import { useEffect, useState } from "react";
import Image from "next/image";

export default function Header() {
  const [time, setTime] = useState("");

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const h = String(now.getHours()).padStart(2, "0");
      const m = String(now.getMinutes()).padStart(2, "0");
      const s = String(now.getSeconds()).padStart(2, "0");
      setTime(`${h}:${m}:${s}`);
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="site-header">
      <div className="header-inner">
        <div className="header-brand">
          <Image
            src="/logo.png"
            alt="D'one TV"
            width={220}
            height={100}
            className="header-logo"
            priority
          />
        </div>
        <div className="header-center">
          <div className="digital-clock">
            <span className="clock-label">LOCAL TIME</span>
            <span className="clock-time">{time}</span>
          </div>
        </div>
        <div className="header-right">
          <span className="tournament-badge">FIFA World Cup 2026</span>
        </div>
      </div>
    </header>
  );
}

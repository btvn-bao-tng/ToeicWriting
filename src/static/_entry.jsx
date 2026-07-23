import React from "react";
import ReactDOM from "react-dom/client";
import DOMPurify from "dompurify";

window.React = React;
window.ReactDOM = ReactDOM;
window.TW = window.TW || {};
window.TW.sanitizeHtml = function sanitizeHtml(html) {
  return DOMPurify.sanitize(html || "", {
    ALLOWED_TAGS: [
      "p", "br", "b", "i", "em", "strong", "u", "a", "img", "ul", "ol", "li",
      "h1", "h2", "h3", "h4", "h5", "h6", "span", "div", "blockquote", "code",
      "pre", "hr", "table", "thead", "tbody", "tr", "td", "th", "sub", "sup",
    ],
    ALLOWED_ATTR: ["href", "src", "alt", "title", "class", "target", "rel", "width", "height"],
  });
};

import "./lib/utils.jsx";
import "./lib/markdown.jsx";
import "./lib/api.jsx";
import "./lib/router.jsx";
import "./hooks/use_app_state.jsx";
import "./components/layout.jsx";
import "./components/practice.jsx";
import "./components/vocab.jsx";
import "./components/auth.jsx";
import "./components/mock_exam.jsx";
import "./components/skeleton.jsx";
import "./components/revision.jsx";
import "./components/game.jsx";
import "./pages/tests_page.jsx";
import "./pages/actions_page.jsx";
import "./pages/practice_page.jsx";
import "./pages/mock_page.jsx";
import "./pages/revision_page.jsx";
import "./pages/game_page.jsx";
import "./app.jsx";
import "./main.jsx";

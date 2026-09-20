import { useEffect, useState } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

import {
  Bot,
  LayoutDashboard,
  MessageSquare,
  Package,
  Ticket,
  BookOpen,
  Send,
  Sparkles,
  CheckCircle2,
  Brain,
  Route,
  Wrench,
  Eye,
  History,
  CircleUserRound,
} from "lucide-react";

import "./App.css";

// ============================================================
// BACKEND API
// ============================================================

const API_URL = "http://127.0.0.1:8000";

const CUSTOMER_ID = 3;

const SESSION_ID = "frontend-demo-session";

// ============================================================
// APPLICATION
// ============================================================

function App() {
  // ==========================================================
  // CURRENT PAGE
  // ==========================================================

  const [currentPage, setCurrentPage] = useState("support");

  // ==========================================================
  // ORDERS
  // ==========================================================

  const [orders, setOrders] = useState([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");

  // ==========================================================
  // TICKETS
  // ==========================================================

  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketsError, setTicketsError] = useState("");

  // ==========================================================
  // KNOWLEDGE BASE
  // ==========================================================

  const [knowledgeDocuments, setKnowledgeDocuments] = useState([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState("");
  const [knowledgeTotalChunks, setKnowledgeTotalChunks] =
    useState(0);

  // ==========================================================
  // DASHBOARD
  // ==========================================================

  const [dashboard, setDashboard] = useState(null);
  const [dashboardLoading, setDashboardLoading] =
    useState(false);
  const [dashboardError, setDashboardError] = useState("");

  // ==========================================================
  // CHAT MESSAGES
  // ==========================================================

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your AI Customer Support Assistant. I can help you with orders, products, tickets, returns, refunds and support policies.",
    },
  ]);

  // ==========================================================
  // INPUT
  // ==========================================================

  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);

  // ==========================================================
  // AGENT ACTIVITY
  // ==========================================================

  const [activity, setActivity] = useState([
    {
      icon: <CheckCircle2 size={16} />,
      text: "Agent initialized",
      active: true,
    },
  ]);

  // ==========================================================
  // MEMORY
  // ==========================================================

  const [memory, setMemory] = useState({
    enabled: true,
    contextUsed: false,
  });

  // ==========================================================
  // AGENT INFORMATION
  // ==========================================================

  const [agentInfo, setAgentInfo] = useState({
    agent: "Waiting",
    tool: "None",
  });

  // ==========================================================
  // FETCH ORDERS
  // ==========================================================

  const fetchOrders = async () => {
    setOrdersLoading(true);
    setOrdersError("");

    try {
      const response = await axios.get(
        `${API_URL}/orders`,
        {
          params: {
            customer_id: CUSTOMER_ID,
          },
          timeout: 10000,
        }
      );

      const data = response.data;

      console.log("=================================");
      console.log("ORDERS RESPONSE");
      console.log(data);
      console.log("=================================");

      if (data?.success) {
        setOrders(data.orders || []);
      } else {
        setOrdersError("Unable to load orders.");
      }
    } catch (error) {
      console.error("Orders request failed:", error);

      if (error.response) {
        setOrdersError(
          `The server returned an error (${error.response.status}).`
        );
      } else if (error.request) {
        setOrdersError(
          "Could not connect to the backend. Please make sure FastAPI is running on port 8000."
        );
      } else {
        setOrdersError(
          "Something went wrong while loading orders."
        );
      }
    } finally {
      setOrdersLoading(false);
    }
  };

  // ==========================================================
  // FETCH TICKETS
  // ==========================================================

  const fetchTickets = async () => {
    setTicketsLoading(true);
    setTicketsError("");

    try {
      const response = await axios.get(
        `${API_URL}/tickets`,
        {
          params: {
            customer_id: CUSTOMER_ID,
          },
          timeout: 10000,
        }
      );

      const data = response.data;

      console.log("=================================");
      console.log("TICKETS RESPONSE");
      console.log(data);
      console.log("=================================");

      if (data?.success) {
        setTickets(data.tickets || []);
      } else {
        setTicketsError(
          "Unable to load support tickets."
        );
      }
    } catch (error) {
      console.error("Tickets request failed:", error);

      if (error.response) {
        setTicketsError(
          `The server returned an error (${error.response.status}).`
        );
      } else if (error.request) {
        setTicketsError(
          "Could not connect to the backend. Please make sure FastAPI is running on port 8000."
        );
      } else {
        setTicketsError(
          "Something went wrong while loading support tickets."
        );
      }
    } finally {
      setTicketsLoading(false);
    }
  };

  // ==========================================================
  // FETCH KNOWLEDGE BASE
  // ==========================================================

  const fetchKnowledgeBase = async () => {
    setKnowledgeLoading(true);
    setKnowledgeError("");

    try {
      const response = await axios.get(
        `${API_URL}/knowledge-base`,
        {
          timeout: 10000,
        }
      );

      const data = response.data;

      console.log("=================================");
      console.log("KNOWLEDGE BASE RESPONSE");
      console.log(data);
      console.log("=================================");

      if (data?.success) {
        setKnowledgeDocuments(data.documents || []);
        setKnowledgeTotalChunks(
          data.total_chunks || 0
        );
      } else {
        setKnowledgeError(
          "Unable to load the knowledge base."
        );
      }
    } catch (error) {
      console.error(
        "Knowledge base request failed:",
        error
      );

      if (error.response) {
        setKnowledgeError(
          `The server returned an error (${error.response.status}).`
        );
      } else if (error.request) {
        setKnowledgeError(
          "Could not connect to the backend. Please make sure FastAPI is running on port 8000."
        );
      } else {
        setKnowledgeError(
          "Something went wrong while loading the knowledge base."
        );
      }
    } finally {
      setKnowledgeLoading(false);
    }
  };

  // ==========================================================
  // FETCH DASHBOARD
  // ==========================================================

  const fetchDashboard = async () => {
    setDashboardLoading(true);
    setDashboardError("");

    try {
      const response = await axios.get(
        `${API_URL}/dashboard/stats`,
        {
          timeout: 10000,
        }
      );

      const data = response.data;

      console.log("=================================");
      console.log("DASHBOARD RESPONSE");
      console.log(data);
      console.log("=================================");

      if (data?.success) {
        setDashboard(data.stats || {});
      } else {
        setDashboardError(
          "Unable to load dashboard statistics."
        );
      }
    } catch (error) {
      console.error(
        "Dashboard request failed:",
        error
      );

      if (error.response) {
        setDashboardError(
          `The server returned an error (${error.response.status}).`
        );
      } else if (error.request) {
        setDashboardError(
          "Could not connect to the backend. Please make sure FastAPI is running on port 8000."
        );
      } else {
        setDashboardError(
          "Something went wrong while loading dashboard statistics."
        );
      }
    } finally {
      setDashboardLoading(false);
    }
  };

  // ==========================================================
  // LOAD PAGE DATA
  // ==========================================================

  useEffect(() => {
    if (currentPage === "orders") {
      fetchOrders();
    }

    if (currentPage === "tickets") {
      fetchTickets();
    }

    if (currentPage === "knowledge") {
      fetchKnowledgeBase();
    }

    if (currentPage === "dashboard") {
      fetchDashboard();
    }
  }, [currentPage]);

  // ==========================================================
  // FORMAT DATE
  // ==========================================================

  const formatDate = (dateString) => {
    if (!dateString) {
      return "Not available";
    }

    try {
      return new Date(dateString).toLocaleDateString(
        "en-IN",
        {
          day: "2-digit",
          month: "short",
          year: "numeric",
        }
      );
    } catch {
      return dateString;
    }
  };

  // ==========================================================
  // FORMAT CURRENCY
  // ==========================================================

  const formatCurrency = (amount) => {
    return `₹${Number(amount || 0).toLocaleString(
      "en-IN"
    )}`;
  };

  // ==========================================================
  // ORDER STATUS CLASS
  // ==========================================================

  const getOrderStatusClass = (status) => {
    const normalizedStatus =
      String(status || "").toLowerCase();

    if (
      normalizedStatus === "delivered" ||
      normalizedStatus === "completed"
    ) {
      return "order-status delivered";
    }

    if (
      normalizedStatus === "shipped" ||
      normalizedStatus === "out_for_delivery"
    ) {
      return "order-status shipped";
    }

    if (
      normalizedStatus === "cancelled" ||
      normalizedStatus === "canceled"
    ) {
      return "order-status cancelled";
    }

    return "order-status processing";
  };

  // ==========================================================
  // TICKET STATUS CLASS
  // ==========================================================

  const getTicketStatusClass = (status) => {
    const normalizedStatus =
      String(status || "").toLowerCase();

    if (
      normalizedStatus === "resolved" ||
      normalizedStatus === "closed"
    ) {
      return "ticket-status resolved";
    }

    if (
      normalizedStatus === "in_progress" ||
      normalizedStatus === "in progress"
    ) {
      return "ticket-status progress";
    }

    return "ticket-status open";
  };

  // ==========================================================
  // TICKET PRIORITY CLASS
  // ==========================================================

  const getTicketPriorityClass = (priority) => {
    const normalizedPriority =
      String(priority || "").toLowerCase();

    if (normalizedPriority === "high") {
      return "ticket-priority high";
    }

    if (normalizedPriority === "low") {
      return "ticket-priority low";
    }

    return "ticket-priority medium";
  };

  // ==========================================================
  // EXTRACT RESPONSE FROM BACKEND
  // ==========================================================

  const extractResponse = (data) => {
    if (
      typeof data?.response === "string" &&
      data.response.trim()
    ) {
      return data.response.trim();
    }

    if (
      typeof data?.result?.message === "string" &&
      data.result.message.trim()
    ) {
      return data.result.message.trim();
    }

    if (
      typeof data?.result?.response === "string" &&
      data.result.response.trim()
    ) {
      return data.result.response.trim();
    }

    if (data?.result?.ticket) {
      const ticket = data.result.ticket;

      return (
        `Support ticket #${ticket.id} has been created successfully. ` +
        `Priority: ${ticket.priority}. ` +
        `Status: ${ticket.status}.`
      );
    }

    if (data?.result?.order) {
      const order = data.result.order;

      return (
        `Order ${order.order_number} is currently ${order.status}. ` +
        `Expected delivery: ${order.expected_delivery}. ` +
        `Total amount: ₹${order.total_amount}.`
      );
    }

    if (data?.result?.product) {
      const product = data.result.product;

      return (
        `${product.name} costs ₹${product.price}. ` +
        `Category: ${product.category}. ` +
        `Stock available: ${product.stock}. ` +
        `Warranty: ${product.warranty_months} months.`
      );
    }

    if (
      Array.isArray(data?.result?.products) &&
      data.result.products.length > 0
    ) {
      return data.result.products
        .map(
          (product) =>
            `${product.name} — ₹${product.price} (Stock: ${product.stock})`
        )
        .join("\n");
    }

    if (
      Array.isArray(data?.result?.results) &&
      data.result.results.length > 0
    ) {
      return data.result.results
        .map((item) => item.content)
        .filter(Boolean)
        .join("\n\n");
    }

    if (
      typeof data?.message === "string" &&
      data.message.trim()
    ) {
      return data.message.trim();
    }

    return "I received your request, but no response was generated.";
  };

  // ==========================================================
  // BUILD AGENT ACTIVITY
  // ==========================================================

  const buildActivity = (data) => {
    const trace = data?.trace || {};

    return [
      {
        icon: <CheckCircle2 size={16} />,
        text: trace.step_1 || "Query received",
        active: true,
      },
      {
        icon: <Brain size={16} />,
        text:
          trace.step_2 ||
          "Conversation memory checked",
        active: true,
      },
      {
        icon: <Route size={16} />,
        text:
          trace.step_3 ||
          `Router selected: ${data?.agent || "agent"}`,
        active: true,
      },
      {
        icon: <Wrench size={16} />,
        text:
          trace.step_4 ||
          `Controlled tool executed: ${data?.tool || "tool"}`,
        active: true,
      },
      {
        icon: <Eye size={16} />,
        text:
          trace.step_5 ||
          "Tool observation received",
        active: true,
      },
      {
        icon: <Sparkles size={16} />,
        text:
          trace.step_6 ||
          "Final response generated",
        active: true,
      },
      ...(trace.step_7
        ? [
            {
              icon: <History size={16} />,
              text: trace.step_7,
              active: true,
            },
          ]
        : []),
    ];
  };

  // ==========================================================
  // UPDATE MEMORY
  // ==========================================================

  const updateMemory = (data) => {
    if (!data?.memory) {
      return;
    }

    setMemory({
      enabled:
        data.memory.enabled !== undefined
          ? data.memory.enabled
          : true,

      contextUsed:
        data.memory.context_used !== undefined
          ? data.memory.context_used
          : false,
    });
  };

  // ==========================================================
  // SEND MESSAGE
  // ==========================================================

  const sendMessage = async () => {
    const userMessage = input.trim();

    if (!userMessage || loading) {
      return;
    }

    setMessages((previousMessages) => [
      ...previousMessages,
      {
        role: "user",
        content: userMessage,
      },
    ]);

    setInput("");
    setLoading(true);

    setAgentInfo({
      agent: "Processing",
      tool: "Waiting...",
    });

    setActivity([
      {
        icon: <Brain size={16} />,
        text: "Processing customer query...",
        active: true,
      },
    ]);

    try {
      const response = await axios.post(
        `${API_URL}/agent/query`,
        {
          query: userMessage,
          customer_id: CUSTOMER_ID,
          session_id: SESSION_ID,
        },
        {
          headers: {
            "Content-Type": "application/json",
          },
          timeout: 30000,
        }
      );

      const data = response.data;

      console.log("=================================");
      console.log("AGENT RESPONSE");
      console.log(data);
      console.log("=================================");

      setAgentInfo({
        agent: data?.agent || "Unknown",
        tool: data?.tool || "None",
      });

      updateMemory(data);

      setActivity(buildActivity(data));

      const assistantResponse =
        extractResponse(data);

      setMessages((previousMessages) => [
        ...previousMessages,
        {
          role: "assistant",
          content: assistantResponse,
        },
      ]);
    } catch (error) {
      console.error(
        "Agent request failed:",
        error
      );

      let errorMessage =
        "Sorry, I couldn't connect to the support agent.";

      if (error.response) {
        errorMessage =
          `The support agent returned an error (${error.response.status}). ` +
          "Please check the backend terminal.";
      } else if (error.request) {
        errorMessage =
          "The support agent could not be reached. " +
          "Please make sure FastAPI is running on port 8000.";
      } else {
        errorMessage =
          "Something went wrong while processing your request.";
      }

      setMessages((previousMessages) => [
        ...previousMessages,
        {
          role: "assistant",
          content: errorMessage,
        },
      ]);

      setAgentInfo({
        agent: "Error",
        tool: "None",
      });

      setActivity([
        {
          icon: <CircleUserRound size={16} />,
          text: "Unable to process request",
          active: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // ==========================================================
  // ENTER KEY
  // ==========================================================

  const handleKeyDown = (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendMessage();
    }
  };

  // ==========================================================
  // QUICK QUERY
  // ==========================================================

  const sendQuickQuery = (query) => {
    if (loading) {
      return;
    }

    setInput(query);
  };

  // ==========================================================
  // PAGE TITLE
  // ==========================================================

  const getPageTitle = () => {
    if (currentPage === "orders") {
      return "Orders";
    }

    if (currentPage === "tickets") {
      return "Support Tickets";
    }

    if (currentPage === "knowledge") {
      return "Knowledge Base";
    }

    if (currentPage === "dashboard") {
      return "Dashboard";
    }

    return "AI Customer Support";
  };

  // ==========================================================
  // PAGE BREADCRUMB
  // ==========================================================

  const getPageName = () => {
    if (currentPage === "orders") {
      return "Orders";
    }

    if (currentPage === "tickets") {
      return "Tickets";
    }

    if (currentPage === "knowledge") {
      return "Knowledge Base";
    }

    if (currentPage === "dashboard") {
      return "Dashboard";
    }

    return "AI Support";
  };

  // ==========================================================
  // UI
  // ==========================================================

  return (
    <div className="app-shell">

      {/* ======================================================
          SIDEBAR
      ====================================================== */}

      <aside className="sidebar">

        <div className="brand">

          <div className="brand-icon">
            <Bot size={23} />
          </div>

          <div>
            <h1>SupportAI</h1>
            <span>Agentic Support</span>
          </div>

        </div>

        <div className="nav-section">

          <p className="nav-title">
            WORKSPACE
          </p>

          <button
            className={`nav-item ${
              currentPage === "support"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setCurrentPage("support")
            }
          >
            <MessageSquare size={18} />
            AI Support
          </button>

          <button
            className={`nav-item ${
              currentPage === "dashboard"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setCurrentPage("dashboard")
            }
          >
            <LayoutDashboard size={18} />
            Dashboard
          </button>

          <button
            className={`nav-item ${
              currentPage === "orders"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setCurrentPage("orders")
            }
          >
            <Package size={18} />
            Orders
          </button>

          <button
            className={`nav-item ${
              currentPage === "tickets"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setCurrentPage("tickets")
            }
          >
            <Ticket size={18} />
            Tickets
          </button>

          <button
            className={`nav-item ${
              currentPage === "knowledge"
                ? "active"
                : ""
            }`}
            onClick={() =>
              setCurrentPage("knowledge")
            }
          >
            <BookOpen size={18} />
            Knowledge Base
          </button>

        </div>

        <div className="sidebar-bottom">

          <div className="system-status">

            <span className="status-dot"></span>

            <div>
              <strong>Agent Online</strong>
              <span>System operational</span>
            </div>

          </div>

          <div className="profile">

            <div className="profile-avatar">
              JD
            </div>

            <div>
              <strong>Demo Customer</strong>

              <span>
                Customer ID: {CUSTOMER_ID}
              </span>
            </div>

          </div>

        </div>

      </aside>

      {/* ======================================================
          MAIN CONTENT
      ====================================================== */}

      <main className="main-content">

        {/* ====================================================
            TOPBAR
        ==================================================== */}

        <header className="topbar">

          <div>

            <div className="breadcrumb">
              Workspace <span>/</span>{" "}
              {getPageName()}
            </div>

            <h2>
              {getPageTitle()}
            </h2>

          </div>

          <div className="topbar-right">

            <div className="memory-pill">

              <Brain size={16} />

              Memory{" "}
              {memory.enabled
                ? "Active"
                : "Off"}

            </div>

            <div className="avatar">
              JD
            </div>

          </div>

        </header>

        {/* ====================================================
            AI SUPPORT PAGE
        ==================================================== */}

        {currentPage === "support" && (

          <div className="workspace">

            <section className="chat-panel">

              <div className="chat-header">

                <div className="assistant-profile">

                  <div className="assistant-icon">
                    <Sparkles size={21} />
                  </div>

                  <div>

                    <h3>
                      Support Assistant
                    </h3>

                    <span>
                      AI-powered customer support •
                      Available 24/7
                    </span>

                  </div>

                </div>

                <div className="online-badge">

                  <span></span>

                  Online

                </div>

              </div>

              <div className="messages">

                {messages.map(
                  (message, index) => (

                    <div
                      className={`message-row ${
                        message.role === "user"
                          ? "user-row"
                          : ""
                      }`}
                      key={index}
                    >

                      {message.role ===
                        "assistant" && (

                        <div className="message-avatar assistant-message-avatar">
                          <Bot size={17} />
                        </div>

                      )}

                      <div
                        className={`message ${
                          message.role === "user"
                            ? "user-message"
                            : "assistant-message"
                        }`}
                      >
                        {message.role === "assistant" ? (
                          <ReactMarkdown>{message.content}</ReactMarkdown>
                        ) : (
                          message.content
                        )}
                      </div>

                      {message.role === "user" && (

                        <div className="message-avatar user-message-avatar">
                          JD
                        </div>

                      )}

                    </div>

                  )
                )}

                {loading && (

                  <div className="message-row">

                    <div className="message-avatar assistant-message-avatar">
                      <Bot size={17} />
                    </div>

                    <div className="assistant-message typing">

                      <span></span>
                      <span></span>
                      <span></span>

                    </div>

                  </div>

                )}

              </div>

              <div className="chat-input-area">

                <div className="suggestions">

                  <button
                    onClick={() =>
                      sendQuickQuery(
                        "Where is my order ORD1002?"
                      )
                    }
                    disabled={loading}
                  >
                    Track an order
                  </button>

                  <button
                    onClick={() =>
                      sendQuickQuery(
                        "Show me product details for product 2"
                      )
                    }
                    disabled={loading}
                  >
                    Product details
                  </button>

                  <button
                    onClick={() =>
                      sendQuickQuery(
                        "What is the warranty period?"
                      )
                    }
                    disabled={loading}
                  >
                    Warranty policy
                  </button>

                </div>

                <div className="input-container">

                  <textarea
                    value={input}
                    onChange={(event) =>
                      setInput(event.target.value)
                    }
                    onKeyDown={handleKeyDown}
                    placeholder="Ask your support assistant..."
                    rows="1"
                    disabled={loading}
                  />

                  <button
                    className="send-button"
                    onClick={sendMessage}
                    disabled={
                      !input.trim() ||
                      loading
                    }
                  >
                    <Send size={19} />
                  </button>

                </div>

                <p className="input-hint">
                  Press <strong>Enter</strong> to send •
                  AI responses are generated using
                  controlled support tools
                </p>

              </div>

            </section>

            {/* AGENT ACTIVITY */}

            <aside className="activity-panel">

              <div className="activity-heading">

                <div>

                  <p className="eyebrow">
                    TRANSPARENT AI
                  </p>

                  <h3>
                    Agent Activity
                  </h3>

                </div>

                <div className="pulse-icon">
                  <Sparkles size={17} />
                </div>

              </div>

              <p className="activity-description">
                Follow how the agent processes
                your request.
              </p>

              <div className="agent-card">

                <div className="agent-card-icon">
                  <Bot size={18} />
                </div>

                <div>

                  <span>
                    ACTIVE AGENT
                  </span>

                  <strong>
                    {agentInfo.agent}
                  </strong>

                </div>

              </div>

              <div className="activity-list">

                {activity.map(
                  (item, index) => (

                    <div
                      className="activity-step"
                      key={index}
                    >

                      <div
                        className={`step-icon ${
                          item.active
                            ? "step-active"
                            : "step-error"
                        }`}
                      >
                        {item.icon}
                      </div>

                      <div className="step-content">

                        <span>
                          STEP {index + 1}
                        </span>

                        <p>
                          {item.text}
                        </p>

                      </div>

                      {index <
                        activity.length - 1 && (
                        <div className="step-line"></div>
                      )}

                    </div>

                  )
                )}

              </div>

              <div className="tool-info">

                <div className="tool-info-header">

                  <Wrench size={16} />

                  <span>
                    CONTROLLED TOOL
                  </span>

                </div>

                <strong>
                  {agentInfo.tool}
                </strong>

                <p>
                  Agent actions are executed through
                  controlled backend tools.
                </p>

              </div>

              <div className="memory-card">

                <div className="memory-card-header">

                  <Brain size={17} />

                  <span>
                    CONVERSATION MEMORY
                  </span>

                </div>

                <div className="memory-status">

                  <span
                    className={
                      memory.contextUsed
                        ? "memory-dot used"
                        : "memory-dot"
                    }
                  ></span>

                  {memory.contextUsed
                    ? "Previous context was used"
                    : "Waiting for conversational context"}

                </div>

                <small>
                  Session: {SESSION_ID}
                </small>

              </div>

            </aside>

          </div>
        )}

        {/* ====================================================
            ORDERS PAGE
        ==================================================== */}

        {currentPage === "orders" && (

          <div className="orders-page">

            <div className="orders-page-header">

              <div>

                <p className="eyebrow">
                  CUSTOMER ORDERS
                </p>

                <h3>
                  Your Orders
                </h3>

                <p>
                  View your recent orders and delivery
                  information.
                </p>

              </div>

              <button
                className="order-refresh-button"
                onClick={fetchOrders}
                disabled={ordersLoading}
              >
                {ordersLoading
                  ? "Refreshing..."
                  : "Refresh"}
              </button>

            </div>

            {ordersLoading && (

              <div className="orders-state">

                <div className="orders-loading-icon">
                  <Package size={25} />
                </div>

                <h3>
                  Loading your orders...
                </h3>

                <p>
                  Fetching orders from the support database.
                </p>

              </div>

            )}

            {!ordersLoading &&
              ordersError && (

                <div className="orders-state">

                  <div className="orders-error-icon">
                    <CircleUserRound size={25} />
                  </div>

                  <h3>
                    Unable to load orders
                  </h3>

                  <p>
                    {ordersError}
                  </p>

                  <button
                    className="order-refresh-button"
                    onClick={fetchOrders}
                  >
                    Try Again
                  </button>

                </div>

              )}

            {!ordersLoading &&
              !ordersError &&
              orders.length === 0 && (

                <div className="orders-state">

                  <div className="orders-loading-icon">
                    <Package size={25} />
                  </div>

                  <h3>
                    No orders found
                  </h3>

                  <p>
                    There are currently no orders
                    associated with this customer.
                  </p>

                </div>

              )}

            {!ordersLoading &&
              !ordersError &&
              orders.length > 0 && (

                <div className="orders-list">

                  {orders.map((order) => (

                    <div
                      className="order-card"
                      key={order.id}
                    >

                      <div className="order-card-header">

                        <div>

                          <span className="order-label">
                            ORDER
                          </span>

                          <h3>
                            {order.order_number}
                          </h3>

                        </div>

                        <span
                          className={getOrderStatusClass(
                            order.status
                          )}
                        >
                          {String(
                            order.status || "processing"
                          )
                            .replaceAll("_", " ")
                            .toUpperCase()}
                        </span>

                      </div>

                      <div className="order-info-grid">

                        <div className="order-info-item">

                          <span>
                            ORDER DATE
                          </span>

                          <strong>
                            {formatDate(
                              order.order_date
                            )}
                          </strong>

                        </div>

                        <div className="order-info-item">

                          <span>
                            EXPECTED DELIVERY
                          </span>

                          <strong>
                            {formatDate(
                              order.expected_delivery
                            )}
                          </strong>

                        </div>

                        <div className="order-info-item">

                          <span>
                            TOTAL
                          </span>

                          <strong>
                            {formatCurrency(
                              order.total_amount
                            )}
                          </strong>

                        </div>

                      </div>

                      <div className="order-products">

                        <div className="order-products-title">
                          <Package size={16} />
                          <span>
                            ORDER ITEMS
                          </span>
                        </div>

                        {order.items?.map(
                          (item, index) => (

                            <div
                              className="order-product-row"
                              key={`${order.id}-${index}`}
                            >

                              <div>

                                <strong>
                                  {item.product_name}
                                </strong>

                                <span>
                                  Quantity:{" "}
                                  {item.quantity}
                                </span>

                              </div>

                              <strong>
                                {formatCurrency(
                                  item.unit_price
                                )}
                              </strong>

                            </div>

                          )
                        )}

                      </div>

                    </div>

                  ))}

                </div>

              )}

          </div>
        )}

        {/* ====================================================
            DASHBOARD PAGE
        ==================================================== */}

        {currentPage === "dashboard" && (

          <div className="orders-page">

            {/* DASHBOARD HEADER */}

            <div className="orders-page-header">

              <div>

                <p className="eyebrow">
                  SYSTEM OVERVIEW
                </p>

                <h3>
                  Dashboard
                </h3>

                <p>
                  Monitor your customer support system,
                  agent activity and knowledge infrastructure.
                </p>

              </div>

              <button
                className="order-refresh-button"
                onClick={fetchDashboard}
                disabled={dashboardLoading}
              >
                {dashboardLoading
                  ? "Refreshing..."
                  : "Refresh"}
              </button>

            </div>

            {/* LOADING */}

            {dashboardLoading && (

              <div className="orders-state">

                <div className="orders-loading-icon">
                  <LayoutDashboard size={25} />
                </div>

                <h3>
                  Loading dashboard...
                </h3>

                <p>
                  Fetching real-time system statistics.
                </p>

              </div>

            )}

            {/* ERROR */}

            {!dashboardLoading &&
              dashboardError && (

                <div className="orders-state">

                  <div className="orders-error-icon">
                    <CircleUserRound size={25} />
                  </div>

                  <h3>
                    Unable to load dashboard
                  </h3>

                  <p>
                    {dashboardError}
                  </p>

                  <button
                    className="order-refresh-button"
                    onClick={fetchDashboard}
                  >
                    Try Again
                  </button>

                </div>

              )}

            {/* DASHBOARD CONTENT */}

            {!dashboardLoading &&
              !dashboardError &&
              dashboard && (

                <>

                  {/* SUMMARY STATISTICS */}

                  <div className="order-info-grid">

                    <div className="order-info-item">

                      <Package size={20} />

                      <span>
                        TOTAL ORDERS
                      </span>

                      <strong>
                        {dashboard.total_orders ?? 0}
                      </strong>

                    </div>

                    <div className="order-info-item">

                      <Ticket size={20} />

                      <span>
                        SUPPORT TICKETS
                      </span>

                      <strong>
                        {dashboard.support_tickets ?? 0}
                      </strong>

                    </div>

                    <div className="order-info-item">

                      <Package size={20} />

                      <span>
                        TOTAL PRODUCTS
                      </span>

                      <strong>
                        {dashboard.total_products ?? 0}
                      </strong>

                    </div>

                    <div className="order-info-item">

                      <CircleUserRound size={20} />

                      <span>
                        TOTAL USERS
                      </span>

                      <strong>
                        {dashboard.total_users ?? 0}
                      </strong>

                    </div>

                    <div className="order-info-item">

                      <BookOpen size={20} />

                      <span>
                        KNOWLEDGE DOCUMENTS
                      </span>

                      <strong>
                        {dashboard.knowledge_documents ?? 0}
                      </strong>

                    </div>

                    <div className="order-info-item">

                      <Brain size={20} />

                      <span>
                        RAG CHUNKS
                      </span>

                      <strong>
                        {dashboard.rag_chunks ?? 0}
                      </strong>

                    </div>

                  </div>

                  {/* AGENT SYSTEM */}

                  <div className="order-card">

                    <div className="order-card-header">

                      <div>

                        <span className="order-label">
                          AGENT SYSTEM
                        </span>

                        <h3>
                          Support Agent
                        </h3>

                      </div>

                      <span className="order-status delivered">
                        ● ONLINE
                      </span>

                    </div>

                    <div className="order-info-grid">

                      <div className="order-info-item">

                        <span>
                          AGENT
                        </span>

                        <strong>
                          ReAct Router
                        </strong>

                      </div>

                      <div className="order-info-item">

                        <span>
                          MEMORY
                        </span>

                        <strong>
                          Enabled
                        </strong>

                      </div>

                      <div className="order-info-item">

                        <span>
                          RETRIEVAL
                        </span>

                        <strong>
                          Semantic RAG
                        </strong>

                      </div>

                    </div>

                  </div>

                  {/* KNOWLEDGE INFRASTRUCTURE */}

                  <div className="order-card">

                    <div className="order-card-header">

                      <div>

                        <span className="order-label">
                          KNOWLEDGE INFRASTRUCTURE
                        </span>

                        <h3>
                          Semantic RAG
                        </h3>

                      </div>

                      <span className="order-status delivered">
                        ACTIVE
                      </span>

                    </div>

                    <div className="order-info-grid">

                      <div className="order-info-item">

                        <span>
                          DOCUMENTS
                        </span>

                        <strong>
                          {dashboard.knowledge_documents ?? 0}
                        </strong>

                      </div>

                      <div className="order-info-item">

                        <span>
                          CHUNKS
                        </span>

                        <strong>
                          {dashboard.rag_chunks ?? 0}
                        </strong>

                      </div>

                      <div className="order-info-item">

                        <span>
                          RETRIEVAL
                        </span>

                        <strong>
                          Semantic RAG
                        </strong>

                      </div>

                    </div>

                  </div>

                </>

              )}

          </div>

        )}

        {/* ====================================================
            TICKETS PAGE
        ==================================================== */}

        {currentPage === "tickets" && (

          <div className="tickets-page">

            <div className="tickets-page-header">

              <div>

                <p className="eyebrow">
                  CUSTOMER SUPPORT
                </p>

                <h3>
                  Your Support Tickets
                </h3>

                <p>
                  View your support requests and their
                  current status.
                </p>

              </div>

              <button
                className="ticket-refresh-button"
                onClick={fetchTickets}
                disabled={ticketsLoading}
              >
                {ticketsLoading
                  ? "Refreshing..."
                  : "Refresh"}
              </button>

            </div>

            {ticketsLoading && (
              <div className="tickets-state">

                <div className="tickets-loading-icon">
                  <Ticket size={25} />
                </div>

                <h3>
                  Loading your tickets...
                </h3>

                <p>
                  Fetching support tickets from the
                  support database.
                </p>

              </div>
            )}

            {!ticketsLoading && ticketsError && (
              <div className="tickets-state">

                <div className="tickets-error-icon">
                  <CircleUserRound size={25} />
                </div>

                <h3>
                  Unable to load tickets
                </h3>

                <p>
                  {ticketsError}
                </p>

                <button
                  className="ticket-refresh-button"
                  onClick={fetchTickets}
                >
                  Try Again
                </button>

              </div>
            )}

            {!ticketsLoading &&
              !ticketsError &&
              tickets.length === 0 && (

                <div className="tickets-state">

                  <div className="tickets-loading-icon">
                    <Ticket size={25} />
                  </div>

                  <h3>
                    No support tickets found
                  </h3>

                  <p>
                    There are currently no support tickets
                    associated with this customer.
                  </p>

                </div>

              )}

            {!ticketsLoading &&
              !ticketsError &&
              tickets.length > 0 && (

                <div className="tickets-list">

                  {tickets.map((ticket) => (

                    <div
                      className="ticket-card"
                      key={ticket.id}
                    >

                      <div className="ticket-card-header">

                        <div>

                          <span className="ticket-label">
                            TICKET
                          </span>

                          <h3>
                            #{ticket.id}
                          </h3>

                        </div>

                        <span
                          className={getTicketStatusClass(
                            ticket.status
                          )}
                        >
                          {String(
                            ticket.status || "open"
                          )
                            .replaceAll("_", " ")
                            .toUpperCase()}
                        </span>

                      </div>

                      <div className="ticket-subject">

                        <span>
                          SUBJECT
                        </span>

                        <h4>
                          {ticket.subject}
                        </h4>

                      </div>

                      <div className="ticket-description">

                        <span>
                          DESCRIPTION
                        </span>

                        <p>
                          {ticket.description}
                        </p>

                      </div>

                      <div className="ticket-info-grid">

                        <div className="ticket-info-item">

                          <span>
                            PRIORITY
                          </span>

                          <strong
                            className={getTicketPriorityClass(
                              ticket.priority
                            )}
                          >
                            {String(
                              ticket.priority || "medium"
                            ).toUpperCase()}
                          </strong>

                        </div>

                        <div className="ticket-info-item">

                          <span>
                            CREATED
                          </span>

                          <strong>
                            {formatDate(
                              ticket.created_at
                            )}
                          </strong>

                        </div>

                        <div className="ticket-info-item">

                          <span>
                            RESOLVED
                          </span>

                          <strong>
                            {formatDate(
                              ticket.resolved_at
                            )}
                          </strong>

                        </div>

                      </div>

                      <div className="ticket-footer">

                        <span>
                          Assigned to
                        </span>

                        <strong>
                          {ticket.assigned_to ||
                            "Unassigned"}
                        </strong>

                      </div>

                    </div>

                  ))}

                </div>

              )}

          </div>

        )}

        {/* ====================================================
            KNOWLEDGE BASE PAGE
        ==================================================== */}

        {currentPage === "knowledge" && (

          <div className="orders-page">

            <div className="orders-page-header">

              <div>

                <p className="eyebrow">
                  SUPPORT KNOWLEDGE
                </p>

                <h3>
                  Knowledge Base
                </h3>

                <p>
                  Browse the policies used by the AI support
                  agent to answer customer questions.
                </p>

              </div>

              <button
                className="order-refresh-button"
                onClick={fetchKnowledgeBase}
                disabled={knowledgeLoading}
              >
                {knowledgeLoading
                  ? "Refreshing..."
                  : "Refresh"}
              </button>

            </div>

            {!knowledgeLoading &&
              !knowledgeError &&
              knowledgeDocuments.length > 0 && (

                <div className="order-info-grid">

                  <div className="order-info-item">

                    <span>
                      DOCUMENTS
                    </span>

                    <strong>
                      {knowledgeDocuments.length}
                    </strong>

                  </div>

                  <div className="order-info-item">

                    <span>
                      TOTAL CHUNKS
                    </span>

                    <strong>
                      {knowledgeTotalChunks}
                    </strong>

                  </div>

                  <div className="order-info-item">

                    <span>
                      RETRIEVAL
                    </span>

                    <strong>
                      Semantic RAG
                    </strong>

                  </div>

                </div>

              )}

            {knowledgeLoading && (

              <div className="orders-state">

                <div className="orders-loading-icon">
                  <BookOpen size={25} />
                </div>

                <h3>
                  Loading knowledge base...
                </h3>

                <p>
                  Fetching support policies from the backend.
                </p>

              </div>

            )}

            {!knowledgeLoading &&
              knowledgeError && (

                <div className="orders-state">

                  <div className="orders-error-icon">
                    <CircleUserRound size={25} />
                  </div>

                  <h3>
                    Unable to load knowledge base
                  </h3>

                  <p>
                    {knowledgeError}
                  </p>

                  <button
                    className="order-refresh-button"
                    onClick={fetchKnowledgeBase}
                  >
                    Try Again
                  </button>

                </div>

              )}

            {!knowledgeLoading &&
              !knowledgeError &&
              knowledgeDocuments.length === 0 && (

                <div className="orders-state">

                  <div className="orders-loading-icon">
                    <BookOpen size={25} />
                  </div>

                  <h3>
                    No knowledge documents found
                  </h3>

                  <p>
                    There are currently no support policies
                    available in the knowledge base.
                  </p>

                </div>

              )}

            {!knowledgeLoading &&
              !knowledgeError &&
              knowledgeDocuments.length > 0 && (

                <div className="orders-list">

                  {knowledgeDocuments.map(
                    (document) => (

                      <div
                        className="order-card"
                        key={document.filename}
                      >

                        <div className="order-card-header">

                          <div>

                            <span className="order-label">
                              POLICY DOCUMENT
                            </span>

                            <h3>
                              {document.title}
                            </h3>

                          </div>

                          <span className="order-status delivered">
                            {document.chunk_count} CHUNKS
                          </span>

                        </div>

                        <div className="order-info-grid">

                          <div className="order-info-item">

                            <span>
                              FILE
                            </span>

                            <strong>
                              {document.filename}
                            </strong>

                          </div>

                          <div className="order-info-item">

                            <span>
                              CHUNKS
                            </span>

                            <strong>
                              {document.chunk_count}
                            </strong>

                          </div>

                          <div className="order-info-item">

                            <span>
                              SOURCE
                            </span>

                            <strong>
                              Knowledge Base
                            </strong>

                          </div>

                        </div>

                        <div className="order-products">

                          <div className="order-products-title">

                            <BookOpen size={16} />

                            <span>
                              POLICY CONTENT
                            </span>

                          </div>

                          <div className="knowledge-content">

                            <ReactMarkdown>
                              {document.content}
                            </ReactMarkdown>

                          </div>

                        </div>

                      </div>

                    )
                  )}

                </div>

              )}

          </div>

        )}

      </main>

    </div>
  );
}

export default App;
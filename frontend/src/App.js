import "@/App.css";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import AppShell from "@/components/AppShell";
import ProtectedRoute from "@/components/ProtectedRoute";
import AcceptInvitation from "@/pages/AcceptInvitation";
import Dashboard from "@/pages/Dashboard";
import ForgotPassword from "@/pages/ForgotPassword";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import ResetPassword from "@/pages/ResetPassword";
import VerifyEmail from "@/pages/VerifyEmail";
import Members from "@/pages/settings/Members";
import Roles from "@/pages/settings/Roles";
import Sessions from "@/pages/settings/Sessions";
import WorkspaceSettings from "@/pages/settings/WorkspaceSettings";
import ShopifyConnect from "@/pages/shopify/Connect";
import ShopifySync from "@/pages/shopify/Sync";
import RazorpayConnect from "@/pages/razorpay/Connect";
import ReconciliationRun from "@/pages/reconciliation/Run";
import ReconciliationResults from "@/pages/reconciliation/Results";
import ReconciliationExceptions from "@/pages/reconciliation/Exceptions";
import ReportsExport from "@/pages/reports/Export";
import NotificationsPreferences from "@/pages/notifications/Preferences";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/verify-email" element={<VerifyEmail />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route
              path="/invitations/accept"
              element={
                <ProtectedRoute>
                  <AcceptInvitation />
                </ProtectedRoute>
              }
            />
            <Route
              path="/app"
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route index element={<Dashboard />} />
              <Route path="settings" element={<Navigate to="/app/settings/general" replace />} />
              <Route path="settings/general" element={<WorkspaceSettings />} />
              <Route path="settings/members" element={<Members />} />
              <Route path="settings/roles" element={<Roles />} />
              <Route path="settings/sessions" element={<Sessions />} />
              <Route path="shopify" element={<ShopifyConnect />} />
              <Route path="shopify/sync" element={<ShopifySync />} />
              <Route path="razorpay" element={<RazorpayConnect />} />
              <Route path="reconciliation/run" element={<ReconciliationRun />} />
              <Route path="reconciliation/results" element={<ReconciliationResults />} />
              <Route path="reconciliation/exceptions" element={<ReconciliationExceptions />} />
              <Route path="reports" element={<ReportsExport />} />
              <Route path="notifications" element={<NotificationsPreferences />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;

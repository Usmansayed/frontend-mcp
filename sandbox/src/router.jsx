import { createBrowserRouter, Navigate } from 'react-router-dom'

import Layout from './components/Layout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'

import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import NotFound from './pages/NotFound.jsx'

import HelpLayout from './pages/help/HelpLayout.jsx'
import Faq from './pages/help/Faq.jsx'
import { ArticleList, ArticleDetail } from './pages/help/Articles.jsx'
import Contact from './pages/help/Contact.jsx'

import DashboardLayout from './pages/dashboard/DashboardLayout.jsx'
import DashboardHome from './pages/dashboard/DashboardHome.jsx'
import Analytics from './pages/dashboard/Analytics.jsx'
import Reports from './pages/dashboard/Reports.jsx'
import { TeamList, TeamMember, TeamMemberActivity } from './pages/dashboard/Team.jsx'

import SettingsLayout from './pages/settings/SettingsLayout.jsx'
import Profile from './pages/settings/Profile.jsx'
import Security from './pages/settings/Security.jsx'
import Notifications from './pages/settings/Notifications.jsx'
import { BillingPlan, BillingInvoices, InvoiceDetail } from './pages/settings/Billing.jsx'

import ShopHome from './pages/shop/ShopHome.jsx'
import ProductList from './pages/shop/ProductList.jsx'
import ProductDetail from './pages/shop/ProductDetail.jsx'
import Cart from './pages/shop/Cart.jsx'
import CheckoutLayout from './pages/shop/checkout/CheckoutLayout.jsx'
import ShippingStep from './pages/shop/checkout/ShippingStep.jsx'
import PaymentStep from './pages/shop/checkout/PaymentStep.jsx'
import ReviewStep from './pages/shop/checkout/ReviewStep.jsx'
import Confirmation from './pages/shop/checkout/Confirmation.jsx'

import FormsLayout from './pages/forms/FormsLayout.jsx'
import SimpleForm from './pages/forms/SimpleForm.jsx'
import ValidationForm from './pages/forms/ValidationForm.jsx'
import WizardForm from './pages/forms/WizardForm.jsx'
import EdgeLab from './pages/edge/EdgeLab.jsx'
import FlawCase, { FlawGalleryIndex } from './pages/eval/FlawGallery.jsx'

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  { path: '/eval/flaws', element: <FlawGalleryIndex /> },
  { path: '/eval/flaws/:caseId', element: <FlawCase /> },
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Home /> },
      { path: 'edge-lab', element: <EdgeLab /> },

      // Help (public, branched)
      {
        path: 'help',
        element: <HelpLayout />,
        children: [
          { index: true, element: <Navigate to="faq" replace /> },
          { path: 'faq', element: <Faq /> },
          { path: 'articles', element: <ArticleList /> },
          { path: 'articles/:slug', element: <ArticleDetail /> },
          { path: 'contact', element: <Contact /> },
        ],
      },

      // Shop (public) with deep checkout wizard
      { path: 'shop', element: <ShopHome /> },
      { path: 'shop/category/:categoryId', element: <ProductList /> },
      { path: 'shop/product/:productId', element: <ProductDetail /> },
      { path: 'shop/cart', element: <Cart /> },
      {
        path: 'shop/checkout',
        element: <CheckoutLayout />,
        children: [
          { index: true, element: <Navigate to="shipping" replace /> },
          { path: 'shipping', element: <ShippingStep /> },
          { path: 'payment', element: <PaymentStep /> },
          { path: 'review', element: <ReviewStep /> },
          { path: 'confirmation', element: <Confirmation /> },
        ],
      },

      // Forms (public)
      {
        path: 'forms',
        element: <FormsLayout />,
        children: [
          { index: true, element: <Navigate to="simple" replace /> },
          { path: 'simple', element: <SimpleForm /> },
          { path: 'validation', element: <ValidationForm /> },
          { path: 'wizard', element: <WizardForm /> },
        ],
      },
    ],
  },

  // Dashboard (protected, nested, own sidebar layout)
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <DashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <DashboardHome /> },
      { path: 'analytics', element: <Analytics /> },
      { path: 'reports/:period', element: <Reports /> },
      {
        path: 'reports/admin',
        element: (
          <ProtectedRoute requireRole="admin">
            <Reports />
          </ProtectedRoute>
        ),
      },
      { path: 'team', element: <TeamList /> },
      { path: 'team/:memberId', element: <TeamMember /> },
      { path: 'team/:memberId/activity', element: <TeamMemberActivity /> },
    ],
  },

  // Settings (protected, nested, own sidebar layout)
  {
    path: '/settings',
    element: (
      <ProtectedRoute>
        <SettingsLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Navigate to="profile" replace /> },
      { path: 'profile', element: <Profile /> },
      { path: 'security', element: <Security /> },
      { path: 'notifications', element: <Notifications /> },
      { path: 'billing', element: <Navigate to="/settings/billing/plan" replace /> },
      { path: 'billing/plan', element: <BillingPlan /> },
      { path: 'billing/invoices', element: <BillingInvoices /> },
      { path: 'billing/invoices/:invoiceId', element: <InvoiceDetail /> },
    ],
  },

  { path: '*', element: <NotFound /> },
])

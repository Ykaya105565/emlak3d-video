import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { authApi } from "../api/listings";
import { useAuthStore } from "../store/auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setTokens } = useAuthStore();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    company_name: "",
    kvkk_consent: false,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.kvkk_consent) {
      setError("Devam etmek için KVKK metnini onaylamanız gerekmektedir.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await authApi.register(form);
      setTokens(data.access_token, data.refresh_token);
      navigate("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Kayıt başarısız");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-900 to-brand-600 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Emlak 3D Platform</h1>
        <p className="text-gray-500 text-sm mb-8">Yeni emlakçı hesabı oluşturun</p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {[
            { key: "full_name", label: "Ad Soyad", type: "text" },
            { key: "company_name", label: "Şirket / Ofis Adı", type: "text" },
            { key: "email", label: "E-posta", type: "email" },
            { key: "password", label: "Şifre", type: "password" },
          ].map(({ key, label, type }) => (
            <div key={key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
              <input
                type={type}
                value={(form as any)[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          ))}

          {/* KVKK Onay */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="kvkk"
                checked={form.kvkk_consent}
                onChange={(e) => setForm((f) => ({ ...f, kvkk_consent: e.target.checked }))}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-brand-600"
              />
              <label htmlFor="kvkk" className="text-xs text-gray-600 leading-relaxed">
                <strong>KVKK Aydınlatma Metni:</strong> Kişisel verileriniz, 6698 sayılı Kişisel Verilerin
                Korunması Kanunu kapsamında, emlak ilanı oluşturma ve video üretimi hizmetleri için
                işlenecektir. Verileriniz üçüncü taraflarla paylaşılmaz. Onay vermek
                zorundasınız.
              </label>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-brand-600 hover:bg-brand-700 text-white font-medium py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            {loading ? "Hesap oluşturuluyor..." : "Hesap Oluştur"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Zaten hesabınız var mı?{" "}
          <Link to="/login" className="text-brand-600 hover:underline font-medium">
            Giriş Yapın
          </Link>
        </p>
      </div>
    </div>
  );
}

import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.38.4/+esm';

const SUPABASE_URL = 'https://nxmcutaokxyrnvhyjvsj.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_t-kse4BP5x_GuHSAP-UwiQ_auOcZ4Qz';

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

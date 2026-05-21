CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE knia_fault_charts
  ADD COLUMN IF NOT EXISTS accident_party_type text DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS accident_party_label text,
  ADD COLUMN IF NOT EXISTS vehicle_a_role text,
  ADD COLUMN IF NOT EXISTS vehicle_b_role text,
  ADD COLUMN IF NOT EXISTS vulnerable_road_user_type text,
  ADD COLUMN IF NOT EXISTS object_type text,
  ADD COLUMN IF NOT EXISTS scenario_summary_easy text,
  ADD COLUMN IF NOT EXISTS recommended_user_actions jsonb DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS display_tags text[] DEFAULT '{}';

ALTER TABLE knia_fault_chart_chunks
  ADD COLUMN IF NOT EXISTS accident_party_type text DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS display_tags text[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS recommended_user_actions jsonb DEFAULT '[]'::jsonb;

ALTER TABLE knia_fault_rankings
  ADD COLUMN IF NOT EXISTS accident_party_type text DEFAULT 'unknown',
  ADD COLUMN IF NOT EXISTS accident_party_label text,
  ADD COLUMN IF NOT EXISTS display_tags text[] DEFAULT '{}';

CREATE TABLE IF NOT EXISTS knia_accident_type_taxonomy (
  id uuid primary key default gen_random_uuid(),
  accident_party_type text not null unique,
  display_label text not null,
  description text,
  keywords text[] default '{}',
  default_actions jsonb default '[]'::jsonb,
  created_at timestamp default now(),
  updated_at timestamp default now()
);

INSERT INTO knia_accident_type_taxonomy(accident_party_type, display_label, description, keywords, default_actions)
VALUES
('car_vs_car','차대차 사고','자동차와 자동차 사이의 사고',ARRAY['차대차','후미추돌','차선변경','진로변경','교차로','신호위반','좌회전','우회전','직진','끼어들기','주정차 차량 충돌'],
 '["블랙박스 원본을 보관하세요.","상대 차량 번호와 연락처를 확인하세요.","보험사에 사고를 접수하고 사고접수번호를 기록하세요.","차량 파손 사진과 현장 사진을 저장하세요."]'::jsonb),
('car_vs_person','차대사람 사고','자동차와 보행자 사이의 사고',ARRAY['차대사람','보행자','횡단보도','무단횡단','어린이보호구역','민식이법','보행자 보호의무','인명피해'],
 '["먼저 다친 사람이 있는지 확인하세요.","필요하면 119와 112에 신고하세요.","보행자의 상태와 사고 위치를 기록하세요.","블랙박스 원본과 현장 사진을 보관하세요."]'::jsonb),
('car_vs_bicycle','차대자전거 사고','자동차와 자전거 사이의 사고',ARRAY['차대자전거','자전거','자전거도로','우회전 자전거','횡단보도 자전거','측면 충돌','자전거 운전자'],
 '["자전거 운전자의 부상 여부를 먼저 확인하세요.","필요하면 119와 112에 신고하세요.","자전거 진행 방향과 충돌 위치를 기록하세요.","블랙박스와 현장 사진을 보관하세요."]'::jsonb),
('car_vs_object','차대기물 사고','자동차와 시설물, 가드레일, 전봇대, 주차된 물체 등 기물 사이의 사고',ARRAY['차대기물','가드레일','전봇대','중앙분리대','벽','주차장 기둥','시설물','도로 시설물','낙하물','물체 충돌'],
 '["차량 이동이 위험하면 안전한 곳으로 대피하세요.","파손된 시설물 또는 물체 사진을 촬영하세요.","보험사에 단독 또는 기물 사고로 접수하세요.","도로 시설물 파손이 있으면 관리기관 또는 경찰 신고를 검토하세요."]'::jsonb),
('single_vehicle','차량단독 사고','다른 차량이나 보행자 없이 혼자 발생한 사고',ARRAY['차량단독','단독사고','혼자','미끄러짐','빗길','눈길','졸음운전','운전미숙','전복','도로 이탈'],
 '["운전자와 동승자의 부상 여부를 확인하세요.","차량이 도로에 위험하게 멈춰 있다면 안전 조치를 하세요.","보험사에 단독사고로 접수하세요.","블랙박스 원본과 사고 장소 사진을 보관하세요."]'::jsonb),
('unknown','사고유형 확인 필요','사고 대분류를 더 확인해야 하는 사고',ARRAY['사고유형 확인'],
 '["사고 상대가 차량인지, 사람인지, 자전거인지, 기물인지 확인해 주세요.","블랙박스와 현장 사진을 보관하세요.","다친 사람이 있으면 먼저 구호와 신고를 검토하세요."]'::jsonb)
ON CONFLICT(accident_party_type) DO UPDATE SET
  display_label=EXCLUDED.display_label,
  description=EXCLUDED.description,
  keywords=EXCLUDED.keywords,
  default_actions=EXCLUDED.default_actions,
  updated_at=now();

CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_party_type ON knia_fault_charts(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_knia_fault_rankings_party_type ON knia_fault_rankings(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_knia_fault_chart_chunks_party_type ON knia_fault_chart_chunks(accident_party_type);
CREATE INDEX IF NOT EXISTS idx_knia_fault_chart_chunks_display_tags ON knia_fault_chart_chunks USING gin(display_tags);
CREATE INDEX IF NOT EXISTS idx_knia_fault_charts_display_tags ON knia_fault_charts USING gin(display_tags);

UPDATE knia_fault_charts SET accident_party_label = COALESCE(accident_party_label, '사고유형 확인 필요') WHERE accident_party_label IS NULL;
UPDATE knia_fault_rankings SET accident_party_label = COALESCE(accident_party_label, '사고유형 확인 필요') WHERE accident_party_label IS NULL;

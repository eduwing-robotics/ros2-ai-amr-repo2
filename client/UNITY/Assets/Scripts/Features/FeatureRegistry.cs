// FeatureRegistry.cs — 기능 토글 등록소. default_features.json 1회 로드 → RobotFeatureInfo[] 보관.
// robotId=""는 "전체 로봇 공통"이라서 GetFeaturesForRobot은 빈 robotId도 포함해서 반환.
using System.Collections.Generic;
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Features
{
    public class FeatureRegistry
    {
        const string ResourcePath = "FeatureConfig/default_features";

        readonly List<RobotFeatureInfo> _features = new List<RobotFeatureInfo>();

        public IReadOnlyList<RobotFeatureInfo> All => _features;

        public void LoadFromResources()
        {
            _features.Clear();
            var ta = Resources.Load<TextAsset>(ResourcePath);
            if (ta == null)
            {
                Debug.LogWarning($"[FeatureRegistry] '{ResourcePath}' 누락. 빈 컬렉션으로 부팅 계속.");
                return;
            }
            try
            {
                var list = JsonUtility.FromJson<RobotFeatureInfoList>(ta.text);
                if (list?.features != null) _features.AddRange(list.features);
                Debug.Log($"[FeatureRegistry] {_features.Count}개 기능 로드.");
            }
            catch (System.Exception e)
            {
                Debug.LogError($"[FeatureRegistry] 파싱 실패: {e.Message}");
            }
        }

        public RobotFeatureInfo GetById(string featureId)
        {
            return _features.Find(f => f.featureId == featureId);
        }

        // robotId가 일치하거나 ""(전체 공통)인 기능만.
        public List<RobotFeatureInfo> GetFeaturesForRobot(string robotId)
        {
            return _features.FindAll(f => f.robotId == robotId || string.IsNullOrEmpty(f.robotId));
        }
    }
}

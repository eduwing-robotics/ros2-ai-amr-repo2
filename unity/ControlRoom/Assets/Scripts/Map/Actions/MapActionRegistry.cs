// MapActionRegistry.cs — 맵 컨텍스트 메뉴 액션 모음. 빌트인 + SSOT(default_situations.json) 상황 액션 병합.
// GetActions(ctx)로 현재 컨텍스트에 적용 가능한 액션만 반환.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using URHYNIX.ControlRoom.Data;

namespace URHYNIX.ControlRoom.Map.Actions
{
    public class MapActionRegistry
    {
        readonly List<IMapAction> actions = new List<IMapAction>();

        public MapActionRegistry()
        {
            actions.Add(new DispatchHereAction());
            LoadSituations();                       // SSOT 상황 출동 액션
            actions.Add(new AddWaypointAction());
            actions.Add(new MarkProtectedTargetAction());
        }

        void LoadSituations()
        {
            var ta = Resources.Load<TextAsset>("SituationConfig/default_situations");
            if (ta == null) return;
            var list = JsonUtility.FromJson<SituationInfoList>(ta.text);
            if (list?.situations == null) return;
            foreach (var s in list.situations)
                actions.Add(new SituationDispatchAction(s));
        }

        public IEnumerable<IMapAction> GetActions(MapClickContext ctx)
            => actions.Where(a => a.AppliesTo(ctx));
    }
}
